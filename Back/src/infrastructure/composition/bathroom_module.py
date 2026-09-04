"""Composition root: ejecución de Baños V1 sobre el universo físico real.

ETAPA 3 — conectar `BathroomV1Model.simulate()` con sus datos reales:

* Event → punto de referencia operacional (`events.reference_point_*`).
* zonas de servicios/baños (`zones.type == "servicios" AND subtipo == "banos"`)
  con `capacity`, `latitude`, `longitude` y `reference_point_distance`
  (Haversine, reutilizado).
* EventDay → `AttendanceLevel.max_people` (magnitud base) y la secuencia
  completa `EventDayPhase[]` (start_min, end_min, intensity).
* `ServiceConfig` → permanencia `average_duration_min` (MINUTOS): override por
  jornada `(zone_type_id, subtipo, event_day_id)` o default global
  `(zone_type_id, subtipo, event_day_id NULL)`. Se convierte a horas dentro del
  modelo (`BathroomV1Model.duration_hours`).

`BathroomV1Model` NO realiza consultas SQL: recibe entidades de dominio ya
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
from src.domain.models.bathroom_v1_model import BathroomPhaseState, BathroomV1Model
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.infrastructure.composition.prediction_module import (
    SUBTIPO_TO_ZONE_TYPE_SLUG,
    _distance_to_reference,
    _load_attendance_level,
    _load_event_reference_point,
    _load_zone_type_map,
    _resolve_service_duration,
    _resolve_zone_type_id,
    _to_uuid_or_none,
)

BATHROOM_ZONE_TYPE = "servicios"
BATHROOM_SUBTIPO = "banos"


def _resolve_bathroom_zone_type_id(type_map: dict[str, UUID]) -> UUID:
    """Resuelve el zone_type_id del catálogo para las zonas de servicios/baños.

    `zones.type` es una categoría genérica ("servicios") y no el slug del
    catálogo; el slug real de baños vive en el subtipo (banos → bano).
    """
    try:
        return _resolve_zone_type_id(
            type_map, BATHROOM_ZONE_TYPE, BATHROOM_SUBTIPO
        )
    except ValueError:
        raise ValueError(
            f"ZoneType slug {SUBTIPO_TO_ZONE_TYPE_SLUG[BATHROOM_SUBTIPO]!r} "
            "not found in catalog; cannot resolve zone_type_id for bathroom "
            "zones (type='servicios', subtipo='banos')"
        ) from None


@dataclass(frozen=True)
class BathroomSimulationResult:
    """Resultado de ejecutar Baños V1 sobre el universo físico real.

    `phase_results` es la salida de `BathroomV1Model.simulate()`: un estado por
    fase, donde cada estado transporta `occupied` (una clave por zona baños).
    `max_people` y `average_duration_min` conservan los inputs reales resueltos.
    """

    event_id: str
    timestamp: datetime
    bathroom_zones: tuple[Zone, ...]
    phases: tuple[EventDayPhase, ...]
    max_people: int
    average_duration_min: int
    duration_hours: float
    phase_results: tuple[BathroomPhaseState, ...]


async def _load_bathroom_zones(
    db: AsyncSession,
    event_id: str,
    type_map: dict[str, UUID],
    ref_lat: float | None = None,
    ref_lng: float | None = None,
) -> list[Zone]:
    """Obtiene TODAS las zonas de servicios/baños de un evento.

    El filtro vive en la consulta SQL y se re-verifica en la frontera de
    composición para garantizar que ninguna zona no-baños entre al modelo.
    """
    stmt = select(ZoneORM).where(
        ZoneORM.event_id == event_id,
        ZoneORM.type == BATHROOM_ZONE_TYPE,
        ZoneORM.subtipo == BATHROOM_SUBTIPO,
    )
    rows = (await db.execute(stmt)).scalars().all()

    zt_id = _resolve_bathroom_zone_type_id(type_map)

    bathroom_zones: list[Zone] = []
    for r in rows:
        if r.type != BATHROOM_ZONE_TYPE or r.subtipo != BATHROOM_SUBTIPO:
            continue
        bathroom_zones.append(
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
    return bathroom_zones


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


class BathroomModule:
    """Composition root que prepara el universo físico y ejecuta Baños V1.

    Entrega a `BathroomV1Model.simulate()`:
    * `phases`: secuencia completa de EventDayPhase (ordenadas por `start_min`
      dentro de `simulate`, como define su implementación).
    * `zones`: todas las zonas de servicios/baños del evento.
    * `max_people` (AttendanceLevel) y `duration_hours`
      (ServiceConfig.average_duration_min convertida a horas).
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def execute(
        self,
        *,
        timestamp: datetime,
        event_id: str,
        alpha: float | None = None,
    ) -> BathroomSimulationResult | None:
        local_ts = timestamp.astimezone(LOCAL_TZ)

        type_map = await _load_zone_type_map(self._db)
        ref_lat, ref_lng = await _load_event_reference_point(self._db, event_id)
        bathroom_zones = await _load_bathroom_zones(
            self._db, event_id, type_map, ref_lat, ref_lng
        )
        if not bathroom_zones:
            return None

        event_day = await resolve_active_event_day(
            local_ts,
            lambda d: _find_event_day_for_date(self._db, event_id, d),
        )
        if event_day is None:
            return None
        if not event_day.phases:
            return None

        attendance_level = await _load_attendance_level(
            self._db,
            (
                str(event_day.attendance_level_id)
                if event_day.attendance_level_id is not None
                else None
            ),
        )
        if attendance_level is None or attendance_level.max_people is None:
            raise ValueError(
                "AttendanceLevel must define max_people to execute Bathroom V1"
            )

        zone_type_id = _resolve_bathroom_zone_type_id(type_map)
        average_duration_min = await _resolve_service_duration(
            self._db,
            zone_type_id=zone_type_id,
            subtipo=BATHROOM_SUBTIPO,
            event_day_id=event_day.id,
        )

        model = (
            BathroomV1Model(alpha=alpha) if alpha is not None else BathroomV1Model()
        )
        duration_hours = model.duration_hours(average_duration_min)
        phase_results = model.simulate(
            phases=event_day.phases,
            zones=bathroom_zones,
            max_people=attendance_level.max_people,
            duration_hours=duration_hours,
        )

        return BathroomSimulationResult(
            event_id=event_id,
            timestamp=local_ts,
            bathroom_zones=tuple(bathroom_zones),
            phases=event_day.phases,
            max_people=attendance_level.max_people,
            average_duration_min=average_duration_min,
            duration_hours=duration_hours,
            phase_results=tuple(phase_results),
        )


# ---------------------------------------------------------------------------
# ETAPA 4 — puente Baños V1 → ZoneState → TerritorialPrediction → Recommendation
# ---------------------------------------------------------------------------


def _select_active_phase_state(
    result: BathroomSimulationResult,
    active_event_day_phase_id: UUID | None,
) -> BathroomPhaseState | None:
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


def derive_bathroom_zone_state(
    zone: Zone,
    phase_state: BathroomPhaseState,
    base_state: ZoneState | None = None,
    model: BathroomV1Model | None = None,
) -> ZoneState:
    """Construye la ZoneState de una zona de servicios/baños desde el resultado real.

    Mapeo (ETAPA 4):
    * `occupancy_ratio` → `saturation_level` (señal de plenitud del scoring).
    * `free_spaces` → `availability`.
    * `confidence` y `estimated_wait` permanecen `None` (Baños V1 no los
      produce; no se fabrican valores sintéticos).
    * `model_result` conserva el dict completo de métricas del modelo.
    """
    resolved_model = model if model is not None else BathroomV1Model()
    occupied = phase_state.occupied.get(zone.id, 0.0)

    # Eventos imprevistos (RFC §10.2): la fuente de verdad de la ocupación
    # proyectada afectada por eventos es `projected_density` del Context Engine
    # (= capacity × density_factor + accumulated_impact). Baños V1 modela la
    # ocupación físico-operativa pero ignora los eventos operativos; por ello
    # los índices expuestos al usuario se derivan desde `projected_density`
    # (mismas unidades que capacity) en lugar de `occupied` del V1. La
    # `occupied` del V1 se conserva en `model_result` como métrica del modelo.
    is_closed = (
        base_state is not None
        and base_state.operational_state == "CLOSED"
    )
    if is_closed:
        occupancy_ratio = 1.0
        free_ratio = 0.0
        effective_free = 0.0
        source_occupied = float(zone.capacity)
        free_spaces = 0.0
    else:
        base_occupied = float(occupied)
        source_occupied = float(
            base_state.projected_density if base_state is not None else base_occupied
        )

        # Detectar si hay un evento imprevisto activo
        has_event = (
            base_state is not None
            and any("Impacto de evento operativo" in f for f in base_state.reasoning_factors)
        )

        if has_event:
            # CON EVENTO: usar projected_density como capacidad efectiva
            # (el impacto ya redujo/aumentó la densidad proyectada)
            capacity_efectiva = max(0.0, source_occupied)
            effective_occupied = min(capacity_efectiva, base_occupied)
            effective_free = max(0.0, capacity_efectiva - effective_occupied)

            if capacity_efectiva == 0.0:
                occupancy_ratio = 1.0  # Zona cerrada
            else:
                occupancy_ratio = effective_occupied / capacity_efectiva
        else:
            # SIN EVENTO: usar el modelo V1 para ocupación real
            # v1_occupied representa la ocupación calculada por el modelo
            # especializado (Ley de Little para baños, flujo vehicular para parking,
            # stock exponencial para comida)
            effective_occupied = min(float(zone.capacity), base_occupied)
            effective_free = max(0.0, float(zone.capacity) - effective_occupied)
            occupancy_ratio = effective_occupied / float(zone.capacity)

        free_ratio = effective_free / float(zone.capacity)
        free_spaces = effective_free

    metrics = {
        "bathroom_id": str(zone.id),
        "occupied": occupied,
        "source_occupied": source_occupied,
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
        availability=int(round(effective_free)),
        saturation_level=float(occupancy_ratio),
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
            int(base_state.projected_density) if base_state is not None else 0
        ),
        model_result=metrics,
    )


def merge_bathroom_into_prediction(
    prediction: TerritorialPrediction,
    bathroom_result: BathroomSimulationResult | None,
    model: BathroomV1Model | None = None,
) -> TerritorialPrediction:
    """Fusiona las ZoneState de servicios/baños en la predicción base.

    Conserva las zonas normales y reemplaza las ZoneState de zonas de
    servicios/baños por las derivadas del resultado real de Baños V1 (mismo
    `zone_id`, mismo orden). Preserva `timestamp`, `active_phase_id` y
    `active_event_day_phase_id`. Si no hay resultado Baños, devuelve la
    predicción sin cambios.
    """
    if bathroom_result is None:
        return prediction
    phase_state = _select_active_phase_state(
        bathroom_result, prediction.active_event_day_phase_id
    )
    if phase_state is None:
        return prediction

    base_by_id = {zs.zone_id: zs for zs in prediction.zone_states}
    derived_by_id: dict[UUID, ZoneState] = {}
    for zone in bathroom_result.bathroom_zones:
        if zone.type != BATHROOM_ZONE_TYPE or zone.subtipo != BATHROOM_SUBTIPO:
            continue
        derived_by_id[zone.id] = derive_bathroom_zone_state(
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