"""Composition root: ejecución de Food V1 sobre el universo físico real.

ETAPA 3 — conectar `FoodV1Model.simulate()` con sus datos reales:

* Event → punto de referencia operacional (`events.reference_point_*`).
* zonas gastronómicas (`zones.type == "comida"`, TODOS los subtipos de la
  taxonomía) con `capacity`, `latitude`, `longitude` y
  `reference_point_distance` (Haversine, reutilizado).
* EventDay → `AttendanceLevel.max_people` (magnitud base, igual que Baños V1)
  y la secuencia completa `EventDayPhase[]` (start_min, end_min, intensity).
* `ServiceConfig` → permanencia `average_duration_min` (MINUTOS) por SUBTIPO:
  override por jornada `(zone_type_id, subtipo, event_day_id)` o default
  global `(zone_type_id, subtipo, event_day_id NULL)`. La conversión min→h se
  ejecuta UNA vez aquí (frontera de composición) vía
  `FoodV1Model.duration_hours()` antes de invocar el modelo, cuyo núcleo
  trabaja exclusivamente en HORAS.

A diferencia de Baños V1 (una única permanencia), Food V1 resuelve una
permanencia por subtipo presente en las zonas cargadas. El modelo calcula
internamente la permanencia efectiva del sistema `D_eff` (§21, promedio
armónico ponderado por capacidad); esta capa NO la recalcula.

Subtipos fuera de la taxonomía canónica `FOOD_SUBTIPOS` se rechazan con error
claro (no se inventan configuraciones); una zona `comida` con `subtipo NULL`
se resuelve contra la convención `""` (misma que estacionamiento).

`FoodV1Model` NO realiza consultas SQL: recibe entidades de dominio ya
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
from src.domain.models.food_v1_model import FoodPhaseState, FoodV1Model
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.infrastructure.composition.prediction_module import (
    _distance_to_reference,
    _load_attendance_level,
    _load_event_reference_point,
    _load_zone_type_map,
    _resolve_service_duration,
    _resolve_zone_type_id,
    _to_uuid_or_none,
)

FOOD_ZONE_TYPE = "comida"
FOOD_SUBTIPOS = (
    "foodtruck",
    "comida_al_paso",
    "penas",
    "patio_de_comidas",
    "restaurante",
)


def _resolve_food_zone_type_id(type_map: dict[str, UUID]) -> UUID:
    """Resuelve el zone_type_id del catálogo para las zonas gastronómicas.

    A diferencia de baños (type genérico "servicios"), las zonas de comida usan
    el slug del catálogo directamente como `zones.type`.
    """
    try:
        return _resolve_zone_type_id(type_map, FOOD_ZONE_TYPE, None)
    except ValueError:
        raise ValueError(
            f"ZoneType slug {FOOD_ZONE_TYPE!r} "
            "not found in catalog; cannot resolve zone_type_id for food "
            f"zones (type={FOOD_ZONE_TYPE!r})"
        ) from None


@dataclass(frozen=True)
class FoodSimulationResult:
    """Resultado de ejecutar Food V1 sobre el universo físico real.

    `phase_results` es la salida de `FoodV1Model.simulate()`: un estado por
    fase, donde cada estado transporta `occupied` (una clave por zona comida).
    `max_people`, `durations_min` (por subtipo, MINUTOS), `durations_hours`
    (por zona, HORAS) y `d_effective_hours` conservan los inputs reales
    resueltos (D_eff la calcula el modelo, §21).
    """

    event_id: str
    timestamp: datetime
    food_zones: tuple[Zone, ...]
    phases: tuple[EventDayPhase, ...]
    max_people: int
    durations_min: dict[str, int]
    durations_hours: dict[UUID, float]
    d_effective_hours: float
    phase_results: tuple[FoodPhaseState, ...]


def _validate_food_taxonomy(zone: Zone) -> None:
    """Rechaza subtipos fuera de la taxonomía gastronómica canónica.

    `subtipo NULL` se permite (convención `""` para zonas directas, igual que
    estacionamiento). Un subtipo desconocido indica un error de configuración
    territorial: se eleva en lugar de inventar una permanencia.
    """
    if zone.subtipo is not None and zone.subtipo not in FOOD_SUBTIPOS:
        raise ValueError(
            f"Zone {zone.id} ({zone.name!r}) has unknown food subtipo "
            f"{zone.subtipo!r}; expected one of {list(FOOD_SUBTIPOS)}"
        )


async def _load_food_zones(
    db: AsyncSession,
    event_id: str,
    type_map: dict[str, UUID],
    ref_lat: float | None = None,
    ref_lng: float | None = None,
) -> list[Zone]:
    """Obtiene TODAS las zonas gastronómicas de un evento (type == "comida").

    El filtro vive en la consulta SQL y se re-verifica en la frontera de
    composición para garantizar que ninguna zona no-comida entre al modelo.
    """
    stmt = select(ZoneORM).where(
        ZoneORM.event_id == event_id,
        ZoneORM.type == FOOD_ZONE_TYPE,
    )
    rows = (await db.execute(stmt)).scalars().all()

    zt_id = _resolve_food_zone_type_id(type_map)

    food_zones: list[Zone] = []
    for r in rows:
        if r.type != FOOD_ZONE_TYPE:
            continue
        zone = Zone(
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
        _validate_food_taxonomy(zone)
        food_zones.append(zone)
    return food_zones


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


async def _resolve_food_durations_min(
    db: AsyncSession,
    *,
    zones: list[Zone],
    zone_type_id: UUID,
    event_day_id: UUID,
) -> dict[str, int]:
    """Resuelve la permanencia (MINUTOS) por subtipo presente en las zonas.

    Precedencia por subtipo (SERVICIOS_PERSONAS_DISENO.md §3):
    1. override por jornada: `(zone_type_id, subtipo, event_day_id)`.
    2. default global: `(zone_type_id, subtipo, event_day_id IS NULL)`.

    `subtipo=None` compara contra cadena vacía vía COALESCE (el helper ya
    normaliza: lowercase + ñ→n). No se inventan valores: si falta configuración
    para algún subtipo, `_resolve_service_duration` eleva `ValueError`.
    """
    subtipo_keys = sorted({(z.subtipo or "") for z in zones})
    durations_min: dict[str, int] = {}
    for key in subtipo_keys:
        durations_min[key] = await _resolve_service_duration(
            db,
            zone_type_id=zone_type_id,
            subtipo=key or None,
            event_day_id=event_day_id,
        )
    return durations_min


class FoodModule:
    """Composition root que prepara el universo físico y ejecuta Food V1.

    Entrega a `FoodV1Model.simulate()`:
    * `phases`: secuencia completa de EventDayPhase (ordenadas por `start_min`
      dentro de `simulate`, como define su implementación).
    * `zones`: todas las zonas gastronómicas del evento (todos los subtipos).
    * `max_people` (AttendanceLevel) y `durations_hours`: permanencia por zona
      en HORAS (ServiceConfig.average_duration_min convertida una sola vez
      aquí; D_eff la calcula internamente el modelo).
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def execute(
        self,
        *,
        timestamp: datetime,
        event_id: str,
        alpha: float | None = None,
    ) -> FoodSimulationResult | None:
        local_ts = timestamp.astimezone(LOCAL_TZ)

        type_map = await _load_zone_type_map(self._db)
        ref_lat, ref_lng = await _load_event_reference_point(self._db, event_id)
        food_zones = await _load_food_zones(
            self._db, event_id, type_map, ref_lat, ref_lng
        )
        if not food_zones:
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
                "AttendanceLevel must define max_people to execute Food V1"
            )

        zone_type_id = _resolve_food_zone_type_id(type_map)
        durations_min = await _resolve_food_durations_min(
            self._db,
            zones=food_zones,
            zone_type_id=zone_type_id,
            event_day_id=event_day.id,
        )

        model = FoodV1Model(alpha=alpha) if alpha is not None else FoodV1Model()
        durations_hours = {
            zone.id: model.duration_hours(
                durations_min[(zone.subtipo or "")]
            )
            for zone in food_zones
        }
        phase_results = model.simulate(
            phases=event_day.phases,
            zones=food_zones,
            max_people=attendance_level.max_people,
            durations_hours=durations_hours,
        )

        return FoodSimulationResult(
            event_id=event_id,
            timestamp=local_ts,
            food_zones=tuple(food_zones),
            phases=event_day.phases,
            max_people=attendance_level.max_people,
            durations_min=durations_min,
            durations_hours=durations_hours,
            d_effective_hours=phase_results[0].d_effective_hours,
            phase_results=tuple(phase_results),
        )


# ---------------------------------------------------------------------------
# ETAPA 4 — puente Food V1 → ZoneState → TerritorialPrediction → Recommendation
# ---------------------------------------------------------------------------


def _select_active_phase_state(
    result: FoodSimulationResult,
    active_event_day_phase_id: UUID | None,
) -> FoodPhaseState | None:
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


def derive_food_zone_state(
    zone: Zone,
    phase_state: FoodPhaseState,
    base_state: ZoneState | None = None,
    model: FoodV1Model | None = None,
) -> ZoneState:
    """Construye la ZoneState de una zona gastronómica desde el resultado real.

    Mapeo (ETAPA 4):
    * `occupancy_ratio` → `saturation_level` (señal de plenitud del scoring).
    * `free_spaces` → `availability`.
    * `confidence` y `estimated_wait` permanecen `None` (Food V1 no los
      produce; no se fabrican valores sintéticos).
    * `model_result` conserva el dict completo de métricas del modelo,
      incluyendo el `subtipo` gastronómico.
    """
    resolved_model = model if model is not None else FoodV1Model()
    occupied = phase_state.occupied.get(zone.id, 0.0)

    # Eventos imprevistos (RFC §10.2): la fuente de verdad de la ocupación
    # proyectada afectada por eventos es `projected_density` del Context Engine
    # (= capacity × density_factor + accumulated_impact). Food V1 modela la
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

    print(
        f"🔍 FOOD: zone={zone.name} cap={zone.capacity} "
        f"v1_occupied={occupied:.1f} "
        f"projected_density={base_state.projected_density if base_state else 'None'} "
        f"source_occupied={source_occupied:.1f} "
        f"has_event={has_event} "
        f"effective_occupied={effective_occupied:.1f} "
        f"effective_free={effective_free:.1f} "
        f"occupancy_ratio={occupancy_ratio:.3f}"
    )

    metrics = {
        "food_id": str(zone.id),
        "subtipo": zone.subtipo,
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


def merge_food_into_prediction(
    prediction: TerritorialPrediction,
    food_result: FoodSimulationResult | None,
    model: FoodV1Model | None = None,
) -> TerritorialPrediction:
    """Fusiona las ZoneState gastronómicas en la predicción base.

    Conserva las zonas normales y reemplaza las ZoneState de zonas de comida
    por las derivadas del resultado real de Food V1 (mismo `zone_id`, mismo
    orden). Preserva `timestamp`, `active_phase_id` y
    `active_event_day_phase_id`. Si no hay resultado Food, devuelve la
    predicción sin cambios.
    """
    if food_result is None:
        return prediction
    phase_state = _select_active_phase_state(
        food_result, prediction.active_event_day_phase_id
    )
    if phase_state is None:
        return prediction

    base_by_id = {zs.zone_id: zs for zs in prediction.zone_states}
    derived_by_id: dict[UUID, ZoneState] = {}
    for zone in food_result.food_zones:
        if zone.type != FOOD_ZONE_TYPE:
            continue
        derived_by_id[zone.id] = derive_food_zone_state(
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
