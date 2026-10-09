"""OperationalEventAdapter: repositorio deterministico de eventos operativos.

Cumple el contrato `OperationalEventRepository` del Context Engine leyendo la
tabla `operational_events` de Esquema A (modelo V1 de `app.models`) y
traduciendo cada fila activa a una entidad de dominio `OperationalEvent` con el
impacto calculado segun el RFC-OPERATIONAL-EVENTS-V1:

- reduccion_capacidad  -> -effect_value          (porcentaje de reduccion)
- cierre_total         -> -100  (impacto canonico de cierre absoluto)
- aumento_demanda      -> effect_value          (delta absoluto de personas)
- incidente_sin_impacto -> 0

Escala e impacto sobre `projected_density`:

`stage3_zone_behavior_application.apply_zone_behaviors` interpreta el impacto
acumulado asi:

    projected_density = round(capacity * density_factor) + accumulated_impact
    if accumulated_impact <= -100 -> FlowRestriction.CLOSED

Es decir, -100 es un CENTINELA DE ESTADO, no una cantidad. Todo lo que quede
entre -99 y -1 es una degradacion de servicio y la zona sigue abierta.

Por eso los cuatro efectos viven en esa escala y no en un conteo absoluto de
personas:

* `cierre_total` emite el centinela directamente, sin mirar `capacity`.
* `reduccion_capacidad` emite el porcentaje con signo negativo: 20% -> -20,
  100% -> -100 (cierra, que es lo correcto). La version anterior multiplicaba
  por `capacity * density_factor` y devolvia personas; en una zona de 1000 al
  50% daba -250, el clamp lo recortaba a -100 y el motor cerraba una zona que
  solo habia perdido la mitad de su capacidad.
* `aumento_demanda` emite un delta de personas y se acota por abajo en 0 para
  que jamas pueda producir un cierre.

`capacity` y `density_factor` siguen siendo parametros de la firma por
compatibilidad con los llamadores; ningun tipo de efecto depende ya de ellos.

El impacto resultante se normaliza a [-100, 100] (restriccion de la entidad de
dominio `OperationalEvent`). Los eventos con zone_id nulo o zona inexistente se
omiten; si no hay zone_behavior ni fase activa se usa una densidad segura (1.0)
para no subestimar el impacto.

OPCIÓN C - `operational_events` es la única autoridad de cierre por zona.
------------------------------------------------------------------
El cierre se deriva en lectura, no se replica en `zone_behaviors`:
`compute_impact("cierre_total", ...) = -100` y Stage3 lo traduce a
`FlowRestriction.CLOSED`. Las funciones que replicaban el cierre sobre
`zone_behaviors` se eliminaron por ser inviables (esa tabla no tiene `zone_id`,
asi que cerraba todas las zonas del mismo tipo) y por perder la transaccion.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any, NamedTuple
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

# Impacto canonico de cierre total. Es el centinela que
# `stage3_zone_behavior_application.apply_zone_behaviors` ya interpreta como
# cierre: `if accumulated_impact <= -100 -> FlowRestriction.CLOSED`.
# Deliberadamente NO depende de capacity/density_factor: si dependiera, las zonas
# cuya ocupacion proyectada no alcanza 100 personas nunca se cerrarian.
CLOSURE_IMPACT_CANONICAL = -100


class EventDayPhaseRow(NamedTuple):
    """Fase de un dia, materializada desde una fila de columnas.

    Sustituye a la entidad `EventDayPhaseORM` en este adapter: son los mismos
    campos que consume `resolve_active_phase_id`, pero sin estado de sesion que
    pueda expirar. Es lo que hace que el pipeline sea seguro en serverless.
    """

    event_day_id: str
    operational_phase_id: UUID
    start_min: int
    end_min: int

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
    day_phases: Sequence[EventDayPhaseRow],
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
    """Impacto entero de un evento operativo, antes del clamp de `clamp_impact`.

    Convencion de escala (Opcion C)
    ------------------------------
    El impacto es un escalar en la misma escala que el centinela de cierre que
    lee `stage3_zone_behavior_application`:

        if accumulated_impact <= -100 -> FlowRestriction.CLOSED

    Por eso -100 significa "cerrada" y cualquier valor entre -99 y -1 significa
    "degradacion de servicio, la zona sigue abierta". Ese es TODO el contrato.

    - `cierre_total`        -> CLOSURE_IMPACT_CANONICAL (-100). Cierra siempre.
    - `reduccion_capacidad` -> `-effect_value`, es decir, el PORCENTAJE de
                               reduccion con signo negativo. Un 20% da -20 y un
                               100% da -100 (cierra). Antes se computaba
                               `-round(capacity * density_factor * pct / 100)`,
                               un conteo absoluto de personas: en una zona de
                               1000 al 50% daba -250, el clamp lo recortaba a
                               -100 y el motor leia ese -100 como cierre total.
                               Una reduccion moderada hacia desaparecer la zona.
    - `aumento_demanda`     -> `+effect_value` como delta absoluto de personas,
                               acotado por abajo en 0 para que NUNCA pueda
                               producir un cierre.
    - resto                -> 0 (`incidente_sin_impacto` cae aqui).

    Nota de unidades: `stage3` suma el impacto a `projected_density`, que esta
    en personas. Con la escala de porcentaje, un -50 resta 50 personas reales
    de la ocupacion proyectada. Es el criterio pedido (desacoplar el impacto del
    tamano de la zona), pero implica que la reduccion efectiva en una zona
    grande es menor que el porcentaje pedido. Ver REPORTE.

    `capacity` y `density_factor` se conservan en la firma por compatibilidad
    con los llamadores y la suite; ningun tipo de efecto depende ya de ellos.
    """
    if effect_type == "cierre_total":
        return CLOSURE_IMPACT_CANONICAL
    if effect_type == "reduccion_capacidad":
        # Porcentaje de reduccion con signo negativo, no conteo de personas.
        # `validate_effect` acota effect_value a 1..100, asi que el resultado
        # cae en [-100, -1] y solo el 100% alcanza el centinela de cierre.
        return -int(effect_value or 0)
    if effect_type == "aumento_demanda":
        # Delta absoluto de personas. El max(0, ...) es defensivo: impide que
        # un `effect_value` negativo (insertado por SQL en una base sin el CHECK
        # `ck_operational_events_effect_value`) genere un impacto negativo y,
        # con el, un cierre fantasma.
        return max(0, effect_value or 0)
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
        # ── serverless-safe: filas como Mapping, no objetos ORM ───────────────
        # `select(Entidad).mappings()` NO sirve: el RowMapping resultante solo
        # tiene la clave del nombre de la clase y su valor sigue siendo una
        # instancia ORM. Hay que seleccionar COLUMNAS: asi el RowMapping tiene
        # una clave por columna y ningun objeto con estado de sesion, que es lo
        # que dispara lazy-loading (y MissingGreenlet) en Vercel.
        #
        # El bug concreto: mas abajo esta `commit()` (barrido de expirados). Con
        # `expire_on_commit=True` —el default— ese commit expira los objetos ORM
        # ya cargados, y el acceso posterior a `row.zone_id` intenta un refresh
        # lazy desde un contexto sin greenlet -> MissingGreenlet. Con filas de
        # columnas no hay estado que expirar.
        rows = (
            await self._db.execute(
                select(
                    OperationalEventORM.id,
                    OperationalEventORM.event_day_id,
                    OperationalEventORM.zone_id,
                    OperationalEventORM.event_type,
                    OperationalEventORM.effect_type,
                    OperationalEventORM.effect_value,
                    OperationalEventORM.is_incident,
                    OperationalEventORM.start_timestamp,
                    OperationalEventORM.end_timestamp,
                ).where(
                    OperationalEventORM.is_active.is_(True),
                    OperationalEventORM.start_timestamp <= timestamp,
                    OperationalEventORM.end_timestamp > timestamp,
                )
            )
        ).mappings().all()

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
        rows: Sequence[Mapping[str, Any]],
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
        rows: Sequence[Mapping[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        zone_ids = {row["zone_id"] for row in rows if row["zone_id"]}
        if not zone_ids:
            return {}
        stmt = (
            select(ZoneORM.id, ZoneORM.capacity, ZoneORM.type, ZoneORM.subtipo)
            .where(ZoneORM.id.in_(list(zone_ids)))
        )
        zone_rows = (await self._db.execute(stmt)).mappings().all()
        return {str(r["id"]): dict(r) for r in zone_rows}

    async def _load_zone_type_map(self) -> dict[str, UUID]:
        rows = (
            await self._db.execute(select(ZoneTypeORM.id, ZoneTypeORM.slug))
        ).mappings().all()
        return {r["slug"]: UUID(str(r["id"])) for r in rows}

    async def _load_event_day_dates(
        self,
        rows: Sequence[Mapping[str, Any]],
    ) -> dict[str, date]:
        ed_ids = {row["event_day_id"] for row in rows if row["event_day_id"]}
        if not ed_ids:
            return {}
        stmt = (
            select(EventDayORM.id, EventDayORM.date)
            .where(EventDayORM.id.in_(list(ed_ids)))
        )
        ed_rows = (await self._db.execute(stmt)).mappings().all()
        return {str(r["id"]): r["date"] for r in ed_rows}

    async def _load_event_day_phases(
        self,
        rows: Sequence[Mapping[str, Any]],
    ) -> dict[str, list[EventDayPhaseRow]]:
        ed_ids = {row["event_day_id"] for row in rows if row["event_day_id"]}
        if not ed_ids:
            return {}
        stmt = (
            select(
                EventDayPhaseORM.event_day_id,
                EventDayPhaseORM.operational_phase_id,
                EventDayPhaseORM.start_min,
                EventDayPhaseORM.end_min,
            )
            .where(EventDayPhaseORM.event_day_id.in_(list(ed_ids)))
        )
        phase_rows = (await self._db.execute(stmt)).mappings().all()
        grouped: dict[str, list[EventDayPhaseRow]] = {}
        for r in phase_rows:
            # Se materializa un record en vez de devolver la entidad ORM: evita
            # arrastrar estado de sesion por el resto del pipeline. Sigue
            # cumpliendo el contrato de `resolve_active_phase_id`, que solo
            # lee `.operational_phase_id`, `.start_min` y `.end_min`.
            grouped.setdefault(str(r["event_day_id"]), []).append(EventDayPhaseRow(
                event_day_id=str(r["event_day_id"]),
                operational_phase_id=UUID(str(r["operational_phase_id"])),
                start_min=r["start_min"],
                end_min=r["end_min"],
            ))
        return grouped

    async def _load_zone_behaviors(
        self,
        day_phases: dict[str, list[EventDayPhaseRow]],
    ) -> dict[tuple[str, UUID | None], float]:
        phase_ids = {
            phase.operational_phase_id
            for phases in day_phases.values()
            for phase in phases
        }
        if not phase_ids:
            return {}
        stmt = (
            select(
                ZoneBehaviorORM.zone_type_id,
                ZoneBehaviorORM.operational_phase_id,
                ZoneBehaviorORM.density_factor,
            )
            .where(ZoneBehaviorORM.operational_phase_id.in_(list(phase_ids)))
        )
        behavior_rows = (await self._db.execute(stmt)).mappings().all()
        return {
            (str(r["zone_type_id"]), UUID(str(r["operational_phase_id"]))): float(
                r["density_factor"],
            )
            for r in behavior_rows
        }

    def _to_domain_event(
        self,
        row: Mapping[str, Any],
        timestamp: datetime,
        zones: dict[str, dict[str, Any]],
        type_map: dict[str, UUID],
        day_dates: dict[str, date],
        day_phases: dict[str, list[EventDayPhaseRow]],
        behaviors: dict[tuple[str, UUID | None], float],
    ) -> OperationalEvent | None:
        if not row["zone_id"]:
            return None
        zone = zones.get(str(row["zone_id"]))
        if zone is None:
            return None
        zt_id = resolve_zone_type_id(type_map, zone["type"], zone["subtipo"])
        if zt_id is None:
            return None
        event_day_date = day_dates.get(str(row["event_day_id"]))
        if event_day_date is None:
            return None
        current_min = minutes_in_local_day(event_day_date, timestamp)
        phase_id = resolve_active_phase_id(
            day_phases.get(str(row["event_day_id"]), []),
            current_min,
        )

        density = behaviors.get((str(zt_id), phase_id), DEFAULT_DENSITY_FACTOR)
        impact = clamp_impact(
            compute_impact(row["effect_type"], row["effect_value"], zone["capacity"], density)
        )

        return OperationalEvent(
            id=UUID(str(row["id"])) if row["id"] else None,
            target_zone_id=UUID(str(row["zone_id"])),
            impact_value=impact,
            is_incident=row["is_incident"],
            start_timestamp=row["start_timestamp"],
            end_timestamp=row["end_timestamp"],
        )