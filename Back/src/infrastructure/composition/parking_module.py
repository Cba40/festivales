"""Composition root: ejecución de Parking V1 sobre el universo físico real.

ETAPA 3 — conectar `ParkingV1Model.simulate()` con sus datos reales:

* Event → punto de referencia operacional (`events.reference_point_*`).
* zonas Parking (`zones.type == "estacionamiento"`) con `capacity`,
  `available_capacity`, `latitude`, `longitude` y `reference_point_distance`
  (Haversine, reutilizado).
* EventDay → `estimated_vehicles`, `average_parking_duration` y la secuencia
  completa `EventDayPhase[]` (start_min, end_min, intensity).

`ParkingV1Model` NO realiza consultas SQL: recibe entidades de dominio ya
cargadas. Esta capa (composition/infrastructure) es la única que prepara y
ejecuta el modelo sobre datos reales, fuera del Context Engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event_day import EventDay as EventDayORM
from app.models.zone import Zone as ZoneORM
from src.application.context_engine.stage1_context_resolution import (
    LOCAL_TZ,
    resolve_active_event_day,
)
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.zone import Zone
from src.domain.models.parking_v1_model import ParkingPhaseState, ParkingV1Model
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
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
                available_capacity=r.available_capacity,
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


async def _find_event_day_for_date(
    db: AsyncSession,
    event_id: str,
    target_date: date,
) -> EventDay | None:
    """Carga el EventDay de una fecha civil y lo mapea a entidad de dominio."""
    ed_row = (
        await db.execute(
            select(EventDayORM)
            .where(EventDayORM.event_id == event_id)
            .where(EventDayORM.date == target_date)
            .options(selectinload(EventDayORM.phases))
        )
    ).scalar_one_or_none()
    if ed_row is None:
        return None
    return _build_event_day(ed_row)


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

        event_day = await resolve_active_event_day(
            local_ts,
            lambda d: _find_event_day_for_date(self._db, event_id, d),
        )
        if event_day is None:
            return None
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


# ---------------------------------------------------------------------------
# ETAPA 4 — puente Parking V1 → ZoneState → TerritorialPrediction → Recommendation
# ---------------------------------------------------------------------------


def _select_active_phase_state(
    result: ParkingSimulationResult,
    active_event_day_phase_id: UUID | None,
) -> ParkingPhaseState | None:
    """Selecciona el estado de la fase activa (la del timestamp de la predicción).

    `simulate()` ordena las fases por `(start_min, id)` y asigna índices 1..n
    en ese orden; `result.phases` es la misma secuencia. Se empareja por
    `active_event_day_phase_id`. Si no se encuentra (p. ej. timestamp fuera de
    rango), se devuelve el estado más avanzado como cierre defensivo.
    """
    if not result.phase_results:
        return None
    if active_event_day_phase_id is None:
        return result.phase_results[-1]
    ordered = sorted(result.phases, key=lambda p: (p.start_min, str(p.id)))
    for i, phase in enumerate(ordered):
        if phase.id == active_event_day_phase_id:
            if i < len(result.phase_results):
                return result.phase_results[i]
            return None
    return result.phase_results[-1]


def derive_parking_zone_state(
    zone: Zone,
    phase_state: ParkingPhaseState,
    base_state: ZoneState | None = None,
    model: ParkingV1Model | None = None,
) -> ZoneState:
    """Construye la ZoneState de una zona Parking a partir del resultado real.

    Mapeo (ETAPA 4):
    * `occupancy_ratio` → `saturation_level` (señal de plenitud del scoring).
    * `free_spaces` → `availability`.
    * `confidence` y `estimated_wait` permanecen `None` (Parking V1 no los
      produce; no se fabrican valores sintéticos).
    * `model_result` conserva el dict completo de métricas del modelo.
    """
    resolved_model = model if model is not None else ParkingV1Model()
    occupied = phase_state.occupied.get(zone.id, 0.0)
    occupancy_ratio, free_ratio, free_spaces = resolved_model.indices(
        occupied, zone.capacity
    )
    metrics = {
        "parking_id": str(zone.id),
        "occupied": occupied,
        "capacity": zone.capacity,
        "occupancy_ratio": occupancy_ratio,
        "free_ratio": free_ratio,
        "free_spaces": free_spaces,
        "distance": zone.reference_point_distance,
        "unabsorbed": phase_state.unabsorbed,
    }
    return ZoneState(
        zone_id=zone.id,
        operational_state=(
            base_state.operational_state if base_state is not None else "NORMAL"
        ),
        availability=round(free_spaces),
        saturation_level=occupancy_ratio,
        estimated_wait=None,
        confidence=None,
        reasoning_factors=(
            list(base_state.reasoning_factors) if base_state is not None else []
        ),
        active_restriction=(
            base_state.active_restriction if base_state is not None else None
        ),
        type=zone.type,
        subtipo=zone.subtipo,
        projected_density=(
            base_state.projected_density if base_state is not None else 0
        ),
        model_result=metrics,
    )


def merge_parking_into_prediction(
    prediction: TerritorialPrediction,
    parking_result: ParkingSimulationResult | None,
    model: ParkingV1Model | None = None,
) -> TerritorialPrediction:
    """Fusiona las ZoneState Parking en la predicción base del Context Engine.

    Conserva las zonas normales y reemplaza las ZoneState de zonas Parking por
    las derivadas del resultado real de Parking V1 (mismo `zone_id`, mismo
    orden). Preserva `timestamp`, `active_phase_id` y `active_event_day_phase_id`.
    Si no hay resultado Parking, devuelve la predicción sin cambios.
    """
    if parking_result is None:
        return prediction
    phase_state = _select_active_phase_state(
        parking_result, prediction.active_event_day_phase_id
    )
    if phase_state is None:
        return prediction

    base_by_id = {zs.zone_id: zs for zs in prediction.zone_states}
    derived_by_id: dict[UUID, ZoneState] = {}
    for zone in parking_result.parking_zones:
        if zone.type != PARKING_ZONE_TYPE:
            continue
        derived_by_id[zone.id] = derive_parking_zone_state(
            zone, phase_state, base_by_id.get(zone.id), model=model
        )

    combined_states = [
        derived_by_id.get(zs.zone_id, zs) for zs in prediction.zone_states
    ]
    return TerritorialPrediction(
        timestamp=prediction.timestamp,
        zone_states=combined_states,
        active_phase_id=prediction.active_phase_id,
        active_event_day_phase_id=prediction.active_event_day_phase_id,
    )