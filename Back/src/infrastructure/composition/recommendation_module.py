"""Composition root for the recommendation flow.

Wires ContextEngine, GeneratePrediction, RecommendationService,
and GetRecommendations with infrastructure dependencies.
"""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.zone import Zone as ZoneORM
from app.models.zone_type import ZoneType as ZoneTypeORM
from app.models.zone_behavior import ZoneBehavior as ZoneBehaviorORM
from app.models.attendance_level import AttendanceLevel as AttendanceLevelORM
from app.models.event_day import EventDay as EventDayORM
from app.models.event_day_phase import EventDayPhase as EventDayPhaseORM
from app.models.operational_phase import OperationalPhase as OperationalPhaseORM
from app.models.operational_profile import OperationalProfile as OperationalProfileORM
from src.application.context_engine import ContextEngine
from src.application.recommendation.recommendation_service import RecommendationService
from src.application.use_cases.generate_prediction import GeneratePrediction
from src.application.use_cases.get_recommendations import GetRecommendations
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


# ---------------------------------------------------------------------------
# Private helpers — data loading from the legacy ORM layer
# ---------------------------------------------------------------------------

_DEFAULT_OPERATIONAL_PROFILE_NAME = "ActividadExtendida"


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


async def _load_zones(
    db: AsyncSession,
    event_id: str,
    type_map: dict[str, UUID],
) -> list[Zone]:
    stmt = select(ZoneORM).where(ZoneORM.event_id == event_id)
    rows = (await db.execute(stmt)).scalars().all()
    zones: list[Zone] = []
    for r in rows:
        zt_id = type_map.get(r.type)
        if zt_id is None:
            zt_id = UUID(r.type)
        zones.append(Zone(
            id=UUID(r.id),
            name=r.name,
            zone_type_id=zt_id,
            capacity=r.capacity,
            type=r.type,
            subtipo=r.subtipo,
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
    attendance_level_id: str,
) -> AttendanceLevel | None:
    stmt = select(AttendanceLevelORM).where(
        AttendanceLevelORM.id == attendance_level_id,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    return AttendanceLevel(
        id=UUID(row.id),
        name=row.name,
        multiplier=row.global_multiplier,
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
        type_map = await _load_zone_type_map(self._db)
        zones = await _load_zones(self._db, event_id, type_map)
        zone_behaviors = await _load_zone_behaviors(self._db, event_id)

        ed_row = (
            await self._db.execute(
                select(EventDayORM)
                .where(EventDayORM.date == timestamp.date())
                .options(selectinload(EventDayORM.phases))
            )
        ).scalar_one_or_none()
        if ed_row is None:
            return [], None

        attendance_level = await _load_attendance_level(self._db, ed_row.attendance_level_id)
        if attendance_level is None:
            return [], None

        eid = UUID(ed_row.id)

        operational_profile_id = ed_row.operational_profile_id
        if operational_profile_id is None:
            operational_profile_id = await _load_default_operational_profile_id(
                self._db,
            )

        event_day = EventDay(
            id=eid,
            event_date=ed_row.date,
            operational_profile_id=operational_profile_id,
            attendance_level_id=attendance_level.id,
            operational_start_min=ed_row.operational_start_min,
            operational_end_min=ed_row.operational_end_min,
            phases=tuple(
                EventDayPhase(
                    id=UUID(str(p.id)),
                    event_day_id=eid,
                    operational_phase_id=UUID(str(p.operational_phase_id)),
                    start_min=p.start_min,
                    end_min=p.end_min,
                )
                for p in ed_row.phases
            ),
        )

        operational_phases = await _load_operational_phases(
            self._db,
            [UUID(str(p.operational_phase_id)) for p in ed_row.phases],
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
        use_case = GetRecommendations(
            generate_prediction=generate_prediction,
            recommendation_service=recommendation_service,
        )

        recommendations = await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
            operational_phases=operational_phases,
            user_context=user_context,
            mobility_context=mobility_context,
            requested_action=requested_action,
            limit=limit,
        )

        return recommendations, prediction_repo.saved_prediction
