"""Composition root: ejecución de Parking V1 sobre el universo físico real.

ETAPA 3 — conectar `ParkingV1Model.simulate()` con sus datos reales:

* Event → punto de referencia operacional (`events.reference_point_*`).
* zonas Parking (`zones.type == "estacionamiento"`) con `capacity`, `latitude`,
  `longitude` y `reference_point_distance` (Haversine, reutilizado).
* EventDay → `estimated_vehicles`, `average_parking_duration` y la secuencia
  completa `EventDayPhase[]` (start_min, end_min, intensity).

`ParkingV1Model` NO realiza consultas SQL: recibe entidades de dominio ya
cargadas. Esta capa (composition/infrastructure) es la única que prepara y
ejecuta el modelo sobre datos reales, fuera del Context Engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event_day import EventDay as EventDayORM
from app.models.zone import Zone as ZoneORM
from src.application.context_engine.stage1_context_resolution import LOCAL_TZ
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.zone import Zone
from src.domain.models.parking_v1_model import ParkingPhaseState, ParkingV1Model
from src.infrastructure.composition.prediction_module import (
    _distance_to_reference,
    _load_event_reference_point,
    _load_zone_type_map,
    _to_uuid_or_none,
)

PARKING_ZONE_TYPE = "estacionamiento"


@dataclass(frozen=True)
class ParkingSimulationResult:
    """Resultado de ejecutar Parking V1 sobre el universo físico real.

    `phase_results` es la salida de `ParkingV1Model.simulate()`: un estado por
    fase, donde cada estado transporta `occupied` (una clave por zona Parking).
    """

    event_id: str
    timestamp: datetime
    parking_zones: tuple[Zone, ...]
    phases: tuple[EventDayPhase, ...]
    estimated_vehicles: int
    average_parking_duration: float
    phase_results: tuple[ParkingPhaseState, ...]


async def _load_parking_zones(
    db: AsyncSession,
    event_id: str,
    type_map: dict[str, UUID],
    ref_lat: float | None = None,
    ref_lng: float | None = None,
) -> list[Zone]:
    """Obtiene TODAS las zonas Parking de un evento (type == "estacionamiento").

    El filtro vive en la consulta SQL y se re-verifica en la frontera de
    composición para garantizar que ninguna zona no-Parking entre al modelo.
    """
    stmt = select(ZoneORM).where(
        ZoneORM.event_id == event_id,
        ZoneORM.type == PARKING_ZONE_TYPE,
    )
    rows = (await db.execute(stmt)).scalars().all()

    parking_zones: list[Zone] = []
    for r in rows:
        if r.type != PARKING_ZONE_TYPE:
            continue
        zt_id = type_map.get(r.type)
        if zt_id is None:
            zt_id = UUID(r.type)
        parking_zones.append(
            Zone(
                id=UUID(r.id),
                name=r.name,
                zone_type_id=zt_id,
                capacity=r.capacity,
                type=r.type,
                subtipo=r.subtipo,
                latitude=r.latitude,
                longitude=r.longitude,
                reference_point_distance=_distance_to_reference(
                    ref_lat, ref_lng, r.latitude, r.longitude
                ),
            )
        )
    return parking_zones


def _build_event_day(ed_row: object) -> EventDay:
    """Mapea la fila ORM de EventDay (con fases) a la entidad de dominio."""
    eid = UUID(ed_row.id)
    return EventDay(
        id=eid,
        event_date=ed_row.date,
        operational_profile_id=ed_row.operational_profile_id,
        attendance_level_id=_to_uuid_or_none(ed_row.attendance_level_id),
        operational_start_min=ed_row.operational_start_min,
        operational_end_min=ed_row.operational_end_min,
        estimated_vehicles=ed_row.estimated_vehicles,
        average_parking_duration=ed_row.average_parking_duration,
        phases=tuple(
            EventDayPhase(
                id=UUID(str(p.id)),
                event_day_id=eid,
                operational_phase_id=UUID(str(p.operational_phase_id)),
                start_min=p.start_min,
                end_min=p.end_min,
                intensity=p.intensity,
            )
            for p in ed_row.phases
        ),
    )


class ParkingModule:
    """Composition root que prepara el universo físico y ejecuta Parking V1.

    Entrega a `ParkingV1Model.simulate()`:
    * `phases`: secuencia completa de EventDayPhase (ordenadas por `start_min`
      dentro de `simulate`, como define su implementación).
    * `zones`: todas las zonas Parking del evento.
    * `estimated_vehicles` y `duration` (average_parking_duration).
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def execute(
        self,
        *,
        timestamp: datetime,
        event_id: str,
        alpha: float | None = None,
    ) -> ParkingSimulationResult | None:
        local_ts = timestamp.astimezone(LOCAL_TZ)

        type_map = await _load_zone_type_map(self._db)
        ref_lat, ref_lng = await _load_event_reference_point(self._db, event_id)
        parking_zones = await _load_parking_zones(
            self._db, event_id, type_map, ref_lat, ref_lng
        )
        if not parking_zones:
            return None

        ed_row = (
            await self._db.execute(
                select(EventDayORM)
                .where(EventDayORM.event_id == event_id)
                .where(EventDayORM.date == local_ts.date())
                .options(selectinload(EventDayORM.phases))
            )
        ).scalar_one_or_none()
        if ed_row is None:
            return None

        event_day = _build_event_day(ed_row)
        if not event_day.phases:
            return None
        if (
            event_day.estimated_vehicles is None
            or event_day.average_parking_duration is None
        ):
            raise ValueError(
                "EventDay must define estimated_vehicles and "
                "average_parking_duration to execute Parking V1"
            )

        model = ParkingV1Model(alpha=alpha) if alpha is not None else ParkingV1Model()
        phase_results = model.simulate(
            phases=event_day.phases,
            zones=parking_zones,
            estimated_vehicles=event_day.estimated_vehicles,
            duration=event_day.average_parking_duration,
        )

        return ParkingSimulationResult(
            event_id=event_id,
            timestamp=local_ts,
            parking_zones=tuple(parking_zones),
            phases=event_day.phases,
            estimated_vehicles=event_day.estimated_vehicles,
            average_parking_duration=event_day.average_parking_duration,
            phase_results=tuple(phase_results),
        )