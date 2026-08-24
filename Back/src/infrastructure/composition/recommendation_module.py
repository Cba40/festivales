"""Composition root for the recommendation flow.

Wires ContextEngine, GeneratePrediction, RecommendationService,
and GetRecommendations with infrastructure dependencies.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import Event as EventORM
from app.models.zone import Zone as ZoneORM
from app.models.zone_type import ZoneType as ZoneTypeORM
from app.models.zone_behavior import ZoneBehavior as ZoneBehaviorORM
from app.models.attendance_level import AttendanceLevel as AttendanceLevelORM
from app.models.event_day import EventDay as EventDayORM
from app.models.event_day_phase import EventDayPhase as EventDayPhaseORM
from app.models.operational_phase import OperationalPhase as OperationalPhaseORM
from app.models.operational_profile import OperationalProfile as OperationalProfileORM
from src.application.context_engine import ContextEngine
from src.application.context_engine.stage1_context_resolution import (
    LOCAL_TZ,
    resolve_active_event_day,
)
from src.application.recommendation.recommendation_service import RecommendationService
from src.application.use_cases.generate_prediction import GeneratePrediction
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction, ZoneBehavior
from src.domain.ports import (
    EventDayRepository,
    OperationalEventRepository,
    PredictionRepository,
)
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import RequestedAction
from src.domain.recommendation.user_context import UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.infrastructure.composition.parking_module import (
    PARKING_ZONE_TYPE,
    ParkingModule,
    merge_parking_into_prediction,
)
from src.infrastructure.composition.bathroom_module import (
    BATHROOM_SUBTIPO,
    BATHROOM_ZONE_TYPE,
    BathroomModule,
    merge_bathroom_into_prediction,
)
from src.infrastructure.composition.food_module import (
    FOOD_ZONE_TYPE,
    FoodModule,
    merge_food_into_prediction,
)
from src.infrastructure.composition.prediction_module import _resolve_zone_type_id


# ---------------------------------------------------------------------------
# Private helpers — data loading from the legacy ORM layer
# ---------------------------------------------------------------------------

_EARTH_RADIUS_M = 6_371_000.0

_DEFAULT_OPERATIONAL_PROFILE_NAME = "ActividadExtendida"


def _to_uuid_or_none(value: str | UUID | None) -> UUID | None:
    """Normaliza un id varchar (o ya UUID) de la capa ORM a UUID de dominio.

    La columna event_days.attendance_level_id es varchar(36); el dominio
    EventDay exige UUID. La conversión ocurre en la frontera ORM -> dominio.
    """
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(value)


async def _load_default_operational_profile_id(
    db: AsyncSession,
) -> UUID | None:
    stmt = (
        select(OperationalProfileORM.id)
        .where(OperationalProfileORM.name == _DEFAULT_OPERATIONAL_PROFILE_NAME)
    )
    profile_id = (await db.execute(stmt)).scalar_one_or_none()
    if profile_id is None:
        stmt = (
            select(OperationalProfileORM.id)
            .order_by(OperationalProfileORM.name)
            .limit(1)
        )
        profile_id = (await db.execute(stmt)).scalar_one_or_none()
    return profile_id


async def _load_zone_type_map(db: AsyncSession) -> dict[str, UUID]:
    stmt = select(ZoneTypeORM)
    rows = (await db.execute(stmt)).scalars().all()
    return {r.slug: UUID(r.id) for r in rows}


def _haversine_distance_m(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Great-circle distance between two coordinates in meters (Haversine)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return _EARTH_RADIUS_M * c


def _distance_to_reference(
    ref_lat: float | None,
    ref_lng: float | None,
    lat: float | None,
    lng: float | None,
) -> float | None:
    if ref_lat is None or ref_lng is None or lat is None or lng is None:
        return None
    return _haversine_distance_m(ref_lat, ref_lng, lat, lng)


async def _load_event_reference_point(
    db: AsyncSession,
    event_id: str,
) -> tuple[float | None, float | None]:
    stmt = (
        select(
            EventORM.reference_point_latitude,
            EventORM.reference_point_longitude,
        )
        .where(EventORM.id == event_id)
    )
    row = (await db.execute(stmt)).one_or_none()
    if row is None:
        return None, None
    return row.reference_point_latitude, row.reference_point_longitude


async def _load_zones(
    db: AsyncSession,
    event_id: str,
    type_map: dict[str, UUID],
    ref_lat: float | None = None,
    ref_lng: float | None = None,
) -> list[Zone]:
    stmt = select(ZoneORM).where(ZoneORM.event_id == event_id)
    rows = (await db.execute(stmt)).scalars().all()
    zones: list[Zone] = []
    for r in rows:
        zt_id = _resolve_zone_type_id(type_map, r.type, r.subtipo)
        zones.append(Zone(
            id=UUID(r.id),
            name=r.name,
            zone_type_id=zt_id,
            capacity=r.capacity,
            type=r.type,
            subtipo=r.subtipo,
            latitude=r.latitude,
            longitude=r.longitude,
            reference_point_distance=_distance_to_reference(
                ref_lat, ref_lng, r.latitude, r.longitude,
            ),
        ))
    return zones


async def _load_zone_behaviors(
    db: AsyncSession,
    event_id: str,
) -> dict[tuple[UUID, UUID], ZoneBehavior]:
    phase_ids = select(EventDayPhaseORM.operational_phase_id).join(
        EventDayORM,
        EventDayPhaseORM.event_day_id == EventDayORM.id,
    ).where(EventDayORM.event_id == event_id)

    stmt = (
        select(ZoneBehaviorORM)
        .where(ZoneBehaviorORM.operational_phase_id.in_(phase_ids))
    )
    rows = (await db.execute(stmt)).scalars().all()
    result: dict[tuple[UUID, UUID], ZoneBehavior] = {}
    for row in rows:
        zt_id = UUID(str(row.zone_type_id))
        op_id = UUID(str(row.operational_phase_id))
        density = min(max(float(row.density_factor), 0.0), 1.0)
        result[(zt_id, op_id)] = ZoneBehavior(
            id=UUID(str(row.id)),
            zone_type_id=zt_id,
            operational_phase_id=op_id,
            density_factor=density,
            flow_restriction=FlowRestriction(row.flow_restriction),
        )
    return result


async def _load_attendance_level(
    db: AsyncSession,
    attendance_level_id: str | None,
) -> AttendanceLevel | None:
    if attendance_level_id is None:
        return None
    row = (
        await db.execute(
            select(AttendanceLevelORM).where(
                AttendanceLevelORM.id == attendance_level_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    return AttendanceLevel(
        id=row.id,
        event_id=row.event_id,
        name=row.name,
        min_people=row.min_people,
        max_people=row.max_people,
    )


async def _load_operational_phases(
    db: AsyncSession,
    phase_ids: Sequence[UUID],
) -> dict[UUID, OperationalPhase]:
    if not phase_ids:
        return {}
    stmt = (
        select(OperationalPhaseORM)
        .where(OperationalPhaseORM.id.in_(list(phase_ids)))
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {
        UUID(str(r.id)): OperationalPhase(
            id=UUID(str(r.id)),
            name=r.name,
            sequence_order=r.sort_order,
        )
        for r in rows
    }


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

    operational_profile_id = ed_row.operational_profile_id
    if operational_profile_id is None:
        operational_profile_id = await _load_default_operational_profile_id(db)

    eid = UUID(ed_row.id)
    return EventDay(
        id=eid,
        event_date=ed_row.date,
        operational_profile_id=operational_profile_id,
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


# ---------------------------------------------------------------------------
# Private in-memory repository implementations (adapter-level)
# ---------------------------------------------------------------------------

class _PreloadedEventDayRepository(EventDayRepository):
    def __init__(self, event_day: EventDay | None) -> None:
        self._event_day = event_day

    async def find_by_date(self, target_date: date) -> EventDay | None:
        if self._event_day is not None and self._event_day.event_date == target_date:
            return self._event_day
        return None


class _EmptyOperationalEventRepository(OperationalEventRepository):
    async def find_active_by_timestamp(
        self, timestamp: datetime,
    ) -> Sequence[OperationalEvent]:
        return []


class _CapturePredictionRepository(PredictionRepository):
    def __init__(self) -> None:
        self.saved_prediction: TerritorialPrediction | None = None

    async def save(self, prediction: TerritorialPrediction) -> TerritorialPrediction:
        self.saved_prediction = prediction
        return prediction

    async def find_by_timestamp(
        self, timestamp: datetime,
    ) -> TerritorialPrediction | None:
        return None


# ---------------------------------------------------------------------------
# Public composition root
# ---------------------------------------------------------------------------

class RecommendationModule:
    """Assembles and executes the recommendation use case.

    Single responsibility: wire application-layer dependencies together
    (ContextEngine, GeneratePrediction, RecommendationService,
     GetRecommendations) with infrastructure adapters and execute.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def execute(
        self,
        *,
        timestamp: datetime,
        event_id: str,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
        limit: int = 5,
    ) -> tuple[list[ZoneRecommendation], TerritorialPrediction | None]:
        local_ts = timestamp.astimezone(LOCAL_TZ)

        type_map = await _load_zone_type_map(self._db)
        ref_lat, ref_lng = await _load_event_reference_point(self._db, event_id)
        zones = await _load_zones(self._db, event_id, type_map, ref_lat, ref_lng)
        zone_behaviors = await _load_zone_behaviors(self._db, event_id)

        event_day = await resolve_active_event_day(
            local_ts,
            lambda d: _find_event_day_for_date(self._db, event_id, d),
        )
        if event_day is None:
            return [], None

        attendance_level = await _load_attendance_level(
            self._db,
            (
                str(event_day.attendance_level_id)
                if event_day.attendance_level_id is not None
                else None
            ),
        )

        operational_phases = await _load_operational_phases(
            self._db,
            [p.operational_phase_id for p in event_day.phases],
        )

        engine = ContextEngine()
        event_day_repo = _PreloadedEventDayRepository(event_day)
        event_repo = _EmptyOperationalEventRepository()
        prediction_repo = _CapturePredictionRepository()

        generate_prediction = GeneratePrediction(
            engine=engine,
            event_day_repo=event_day_repo,
            operational_event_repo=event_repo,
            prediction_repo=prediction_repo,
        )
        recommendation_service = RecommendationService()

        prediction = await generate_prediction.execute(
            timestamp=local_ts,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
            operational_phases=operational_phases,
        )

        # ETAPA 4 — puente Parking V1 → ZoneState → TerritorialPrediction.
        # Context Engine NO procesa zonas Parking: el puente se ejecuta desde la
        # composición con los datos reales ya disponibles y fusiona la predicción
        # antes del scoring. Solo se activa para acciones de estacionamiento.
        combined = prediction
        if requested_action.type == PARKING_ZONE_TYPE:
            parking_result = await ParkingModule(self._db).execute(
                timestamp=local_ts,
                event_id=event_id,
            )
            combined = merge_parking_into_prediction(prediction, parking_result)

        # ETAPA 4 — puente Baños V1 → ZoneState → TerritorialPrediction.
        # Mismo patrón que Parking V1: el Context Engine NO procesa zonas de
        # servicios/baños; el puente se ejecuta desde la composición y fusiona
        # la predicción antes del scoring. Solo se activa para acciones de baños
        # (type == "servicios" AND subtipo == "banos").
        if (
            requested_action.type == BATHROOM_ZONE_TYPE
            and requested_action.subtipo == BATHROOM_SUBTIPO
        ):
            bathroom_result = await BathroomModule(self._db).execute(
                timestamp=local_ts,
                event_id=event_id,
            )
            combined = merge_bathroom_into_prediction(combined, bathroom_result)

        # ETAPA 4 — puente Food V1 → ZoneState → TerritorialPrediction.
        # Mismo patrón que Parking V1 y Baños V1: el Context Engine NO procesa
        # zonas gastronómicas; el puente se ejecuta desde la composición y
        # fusiona la predicción antes del scoring. Solo se activa para acciones
        # de comida (type == "comida", todos los subtipos).
        if requested_action.type == FOOD_ZONE_TYPE:
            food_result = await FoodModule(self._db).execute(
                timestamp=local_ts,
                event_id=event_id,
            )
            combined = merge_food_into_prediction(combined, food_result)

        zone_coordinates: dict[UUID, tuple[float, float]] | None = None
        if (
            mobility_context.latitude is not None
            and mobility_context.longitude is not None
        ):
            zone_coordinates = {
                zone.id: (zone.latitude, zone.longitude)
                for zone in zones
                if zone.latitude is not None and zone.longitude is not None
            }

        recommendations = recommendation_service.recommend(
            prediction=combined,
            user_context=user_context,
            mobility_context=mobility_context,
            requested_action=requested_action,
            limit=limit,
            zone_coordinates=zone_coordinates,
        )

        return recommendations, combined
