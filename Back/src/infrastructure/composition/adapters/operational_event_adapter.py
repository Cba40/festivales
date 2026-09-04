"""OperationalEventAdapter: repositorio deterministico de eventos operativos.

Cumple el contrato `OperationalEventRepository` del Context Engine leyendo la
tabla `operational_events` de Esquema A (modelo V1 de `app.models`) y
traduciendo cada fila activa a una entidad de dominio `OperationalEvent` con el
impacto calculado segun el RFC-OPERATIONAL-EVENTS-V1:

- reduccion_capacidad  -> -round(capacity * density_factor * effect_value / 100)
- cierre_total         -> -round(capacity * density_factor)
- aumento_demanda      -> effect_value
- incidente_sin_impacto -> 0

`density_factor` se obtiene de `zone_behaviors` para el par
(zone_type, fase operativa activa) en el timestamp; `capacity` desde `zones`.

El impacto resultante se normaliza a [-100, 100] (restringido por la entidad de
dominio `OperationalEvent`). Los eventos con zone_id nulo o zona inexistente se
omiten; si no hay zone_behavior ni fase activa se usa una densidad segura (1.0)
para no subestimar el impacto.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_day import EventDay as EventDayORM
from app.models.event_day_phase import EventDayPhase as EventDayPhaseORM
from app.models.operational_event import OperationalEvent as OperationalEventORM
from app.models.zone import Zone as ZoneORM
from app.models.zone_behavior import ZoneBehavior as ZoneBehaviorORM
from app.models.zone_type import ZoneType as ZoneTypeORM
from src.domain.entities.operational_event import OperationalEvent
from src.domain.ports import OperationalEventRepository

LOCAL_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

DEFAULT_DENSITY_FACTOR = 1.0

_SUBTIPO_TO_ZONE_TYPE_SLUG = {
    "banos": "bano",
    "hidratacion": "hidratacion",
    "descanso": "descanso",
}


def minutes_in_local_day(event_date: date, timestamp: datetime) -> int:
    """Minutos desde la medianoche de `event_date` hasta `timestamp` (tz local).

    Replica la resolucion temporal del Context Engine (`_to_current_min` de
    `stage1_context_resolution`): soporta jornadas que cruzan medianoche.
    """
    local_ts = timestamp.astimezone(LOCAL_TZ)
    days_diff = (local_ts.date() - event_date).days
    return days_diff * 1440 + local_ts.hour * 60 + local_ts.minute


def resolve_zone_type_id(
    type_map: dict[str, UUID],
    zone_type: str,
    subtipo: str | None,
) -> UUID | None:
    """Resuelve el zone_type_id de una zona desde el catalogo de `zone_types`.

    Prioridad: (1) `type` como slug directo; (2) `subtipo` mapeado a slug.
    Devuelve None si el slug no existe en el catalogo (la zona se omite).
    """
    zt_id = type_map.get(zone_type)
    if zt_id is not None:
        return zt_id
    slug = _SUBTIPO_TO_ZONE_TYPE_SLUG.get((subtipo or "").lower())
    if slug is not None:
        return type_map.get(slug)
    return None


def resolve_active_phase_id(
    day_phases: Sequence[EventDayPhaseORM],
    current_min: int,
) -> UUID | None:
    """Fase operativa activa para `current_min` (ventana [start_min, end_min))."""
    for phase in day_phases:
        if phase.start_min <= current_min < phase.end_min:
            return UUID(str(phase.operational_phase_id))
    return None


def compute_impact(
    effect_type: str,
    effect_value: int | None,
    capacity: int,
    density_factor: float,
) -> int:
    """Impacto entero segun RFC-OPERATIONAL-EVENTS-V1 (antes del clamp [-100,100])."""
    if effect_type == "cierre_total":
        return -round(capacity * density_factor)
    if effect_type == "reduccion_capacidad":
        return -round(capacity * density_factor * (effect_value or 0) / 100)
    if effect_type == "aumento_demanda":
        return effect_value or 0
    return 0


def clamp_impact(value: int) -> int:
    """Normaliza el impacto a [-100, 100] (restriccion de la entidad de dominio)."""
    return max(-100, min(100, value))


class OperationalEventAdapter(OperationalEventRepository):
    """OperationalEventRepository sobre la tabla V1 `operational_events`.

    Recibe `db: AsyncSession` y expone `find_active_by_timestamp(timestamp)`,
    usado por `GeneratePrediction`. `save` no aplica en este adapter (solo
    lectura); la persistencia de eventos operativos vive en la capa API/CRUD.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def find_active_by_timestamp(
        self, timestamp: datetime,
    ) -> Sequence[OperationalEvent]:
        rows = (
            await self._db.execute(
                select(OperationalEventORM).where(
                    OperationalEventORM.is_active.is_(True),
                    OperationalEventORM.start_timestamp <= timestamp,
                    OperationalEventORM.end_timestamp > timestamp,
                )
            )
        ).scalars().all()

        if not rows:
            return []

        stale_result = await self._db.execute(
            select(OperationalEventORM.id).where(
                OperationalEventORM.is_active.is_(True),
                OperationalEventORM.end_timestamp <= timestamp,
            )
        )
        expired_ids = [r for (r,) in stale_result.all()]
        if expired_ids:
            await self._db.execute(
                update(OperationalEventORM)
                .where(OperationalEventORM.id.in_(expired_ids))
                .values(is_active=False)
            )
            await self._db.commit()

        return await self._build_domain_events(rows, timestamp)

    async def save(self, event: OperationalEvent) -> OperationalEvent:
        raise NotImplementedError(
            "OperationalEventAdapter is read-only in RFC-OPERATIONAL-EVENTS-V1; "
            "la persistencia de eventos operativos vive en la capa API/CRUD."
        )

    async def _build_domain_events(
        self,
        rows: Sequence[OperationalEventORM],
        timestamp: datetime,
    ) -> list[OperationalEvent]:
        zones = await self._load_zones(rows)
        type_map = await self._load_zone_type_map()
        day_dates = await self._load_event_day_dates(rows)
        day_phases = await self._load_event_day_phases(rows)
        behaviors = await self._load_zone_behaviors(day_phases)

        events: list[OperationalEvent] = []
        for row in rows:
            event = self._to_domain_event(
                row,
                timestamp,
                zones,
                type_map,
                day_dates,
                day_phases,
                behaviors,
            )
            if event is not None:
                events.append(event)

        return events

    async def _load_zones(
        self,
        rows: Sequence[OperationalEventORM],
    ) -> dict[str, object]:
        zone_ids = {row.zone_id for row in rows if row.zone_id}
        if not zone_ids:
            return {}
        stmt = (
            select(ZoneORM.id, ZoneORM.capacity, ZoneORM.type, ZoneORM.subtipo)
            .where(ZoneORM.id.in_(list(zone_ids)))
        )
        zone_rows = (await self._db.execute(stmt)).all()
        return {str(row.id): row for row in zone_rows}

    async def _load_zone_type_map(self) -> dict[str, UUID]:
        rows = (await self._db.execute(select(ZoneTypeORM))).scalars().all()
        return {row.slug: UUID(str(row.id)) for row in rows}

    async def _load_event_day_dates(
        self,
        rows: Sequence[OperationalEventORM],
    ) -> dict[str, date]:
        ed_ids = {row.event_day_id for row in rows if row.event_day_id}
        if not ed_ids:
            return {}
        stmt = (
            select(EventDayORM.id, EventDayORM.date)
            .where(EventDayORM.id.in_(list(ed_ids)))
        )
        ed_rows = (await self._db.execute(stmt)).all()
        return {str(row.id): row.date for row in ed_rows}

    async def _load_event_day_phases(
        self,
        rows: Sequence[OperationalEventORM],
    ) -> dict[str, list[EventDayPhaseORM]]:
        ed_ids = {row.event_day_id for row in rows if row.event_day_id}
        if not ed_ids:
            return {}
        stmt = (
            select(EventDayPhaseORM)
            .where(EventDayPhaseORM.event_day_id.in_(list(ed_ids)))
        )
        phase_rows = (await self._db.execute(stmt)).scalars().all()
        grouped: dict[str, list[EventDayPhaseORM]] = {}
        for phase in phase_rows:
            grouped.setdefault(str(phase.event_day_id), []).append(phase)
        return grouped

    async def _load_zone_behaviors(
        self,
        day_phases: dict[str, list[EventDayPhaseORM]],
    ) -> dict[tuple[str, UUID | None], float]:
        phase_ids = {
            UUID(str(phase.operational_phase_id))
            for phases in day_phases.values()
            for phase in phases
        }
        if not phase_ids:
            return {}
        stmt = (
            select(ZoneBehaviorORM)
            .where(ZoneBehaviorORM.operational_phase_id.in_(list(phase_ids)))
        )
        behavior_rows = (await self._db.execute(stmt)).scalars().all()
        return {
            (str(behavior.zone_type_id), UUID(str(behavior.operational_phase_id))): float(
                behavior.density_factor,
            )
            for behavior in behavior_rows
        }

    def _to_domain_event(
        self,
        row: OperationalEventORM,
        timestamp: datetime,
        zones: dict[str, object],
        type_map: dict[str, UUID],
        day_dates: dict[str, date],
        day_phases: dict[str, list[EventDayPhaseORM]],
        behaviors: dict[tuple[str, UUID | None], float],
    ) -> OperationalEvent | None:
        if not row.zone_id:
            return None
        zone = zones.get(str(row.zone_id))
        if zone is None:
            return None
        zt_id = resolve_zone_type_id(type_map, zone.type, zone.subtipo)
        if zt_id is None:
            return None
        event_day_date = day_dates.get(str(row.event_day_id))
        if event_day_date is None:
            return None
        current_min = minutes_in_local_day(event_day_date, timestamp)
        phase_id = resolve_active_phase_id(
            day_phases.get(str(row.event_day_id), []),
            current_min,
        )
        
        density = behaviors.get((str(zt_id), phase_id), DEFAULT_DENSITY_FACTOR)
        impact = clamp_impact(
            compute_impact(row.effect_type, row.effect_value, zone.capacity, density)
        )
        
        return OperationalEvent(
            id=UUID(str(row.id)) if row.id else None,
            target_zone_id=UUID(str(row.zone_id)),
            impact_value=impact,
            is_incident=row.is_incident,
            start_timestamp=row.start_timestamp,
            end_timestamp=row.end_timestamp,
        )