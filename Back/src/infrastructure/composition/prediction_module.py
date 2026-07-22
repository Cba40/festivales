"""Composition root for the prediction flow.

Wires ContextEngine, GeneratePrediction, and
GetTerritorialPrediction with infrastructure dependencies.
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
from app.models.operational_profile import OperationalProfile as OperationalProfileORM
from app.models.operational_phase import OperationalPhase as OperationalPhaseORM
from src.application.context_engine import ContextEngine
from src.application.use_cases.generate_prediction import GeneratePrediction
from src.application.use_cases.get_prediction import GetTerritorialPrediction
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.operational_event import OperationalEvent
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.operational_profile import OperationalProfile
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction, ZoneBehavior
from src.domain.ports import (
    EventDayRepository,
    OperationalEventRepository,
    OperationalProfileRepository,
    PredictionRepository,
)
from src.domain.value_objects.territorial_prediction import TerritorialPrediction


# ---------------------------------------------------------------------------
# Private helpers — data loading from the legacy ORM layer
# ---------------------------------------------------------------------------

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
        ))
    return zones


async def _load_zone_behaviors(
    db: AsyncSession,
    event_id: str,
) -> dict[tuple[UUID, UUID], ZoneBehavior]:
    profile_ids = select(OperationalProfileORM.id).join(
        EventDayORM,
        OperationalProfileORM.id == EventDayORM.operational_profile_id,
    ).where(EventDayORM.event_id == event_id)

    stmt = (
        select(ZoneBehaviorORM)
        .join(
            OperationalPhaseORM,
            ZoneBehaviorORM.operational_phase_id == OperationalPhaseORM.id,
        )
        .where(OperationalPhaseORM.operational_profile_id.in_(profile_ids))
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
    event_id: str,
) -> AttendanceLevel | None:
    stmt = select(AttendanceLevelORM).where(
        AttendanceLevelORM.event_id == event_id,
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    return AttendanceLevel(
        id=UUID(row.id),
        name=row.name,
        multiplier=row.global_multiplier,
    )


async def _load_operational_profile(
    db: AsyncSession,
    profile_id: UUID,
) -> OperationalProfile | None:
    stmt = (
        select(OperationalProfileORM)
        .where(OperationalProfileORM.id == profile_id)
        .options(selectinload(OperationalProfileORM.phases))
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    phases = tuple(
        OperationalPhase(
            id=UUID(str(p.id)),
            name=p.name,
            sequence_order=p.sort_order,
        )
        for p in row.phases
    )
    return OperationalProfile(
        id=UUID(str(row.id)),
        name=row.name,
        phases=phases,
    )


# ---------------------------------------------------------------------------
# Private in-memory repository implementations (adapter-level)
# ---------------------------------------------------------------------------

class _PreloadedEventDayRepository(EventDayRepository):
    def __init__(self, event_day: EventDay | None) -> None:
        self._event_day = event_day

    async def find_by_date(self, target_date: datetime | date) -> EventDay | None:
        if self._event_day is not None and self._event_day.event_date == target_date:
            return self._event_day
        return None


class _PreloadedOperationalProfileRepository(OperationalProfileRepository):
    def __init__(self, profile: OperationalProfile | None) -> None:
        self._profile = profile

    async def find_by_id(self, profile_id: UUID) -> OperationalProfile | None:
        if self._profile is not None and self._profile.id == profile_id:
            return self._profile
        return None


class _EmptyOperationalEventRepository(OperationalEventRepository):
    async def find_active_by_timestamp(
        self, timestamp: datetime,
    ) -> Sequence[OperationalEvent]:
        return []


class _CapturePredictionRepository(PredictionRepository):
    def __init__(self) -> None:
        self.saved: TerritorialPrediction | None = None

    async def save(self, prediction: TerritorialPrediction) -> TerritorialPrediction:
        self.saved = prediction
        return prediction

    async def find_by_timestamp(
        self, timestamp: datetime,
    ) -> TerritorialPrediction | None:
        if self.saved is not None and self.saved.timestamp == timestamp:
            return self.saved
        return None


class _ReturnSavedPredictionRepository(PredictionRepository):
    def __init__(self) -> None:
        self.saved: TerritorialPrediction | None = None

    async def save(self, prediction: TerritorialPrediction) -> TerritorialPrediction:
        self.saved = prediction
        return prediction

    async def find_by_timestamp(
        self, timestamp: datetime,
    ) -> TerritorialPrediction | None:
        return self.saved


# ---------------------------------------------------------------------------
# Public composition root
# ---------------------------------------------------------------------------

class PredictionModule:
    """Assembles and executes the prediction use case.

    Single responsibility: wire application-layer dependencies together
    (ContextEngine, GeneratePrediction, GetTerritorialPrediction)
    with infrastructure adapters and execute.
    """

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def execute(
        self,
        *,
        timestamp: datetime,
        event_id: str,
    ) -> TerritorialPrediction | None:
        type_map = await _load_zone_type_map(self._db)
        zones = await _load_zones(self._db, event_id, type_map)
        if not zones:
            return None

        zone_behaviors = await _load_zone_behaviors(self._db, event_id)

        attendance_level = await _load_attendance_level(self._db, event_id)
        if attendance_level is None:
            return None

        ed_row = (
            await self._db.execute(
                select(EventDayORM).where(EventDayORM.date == timestamp.date()),
            )
        ).scalar_one_or_none()
        if ed_row is None:
            return None

        operational_profile = await _load_operational_profile(
            self._db, ed_row.operational_profile_id,
        )
        if operational_profile is None:
            return None

        eid = UUID(ed_row.id)

        event_day = EventDay(
            id=eid,
            event_date=ed_row.date,
            operational_profile_id=UUID(str(ed_row.operational_profile_id)),
            attendance_level_id=attendance_level.id,
            operational_start_min=ed_row.operational_start_min,
            operational_end_min=ed_row.operational_end_min,
            phases=tuple(
                EventDayPhase(
                    id=UUID(str(p.id)),
                    event_day_id=eid,
                    operational_phase_id=p.id,
                    start_min=p.start_min,
                    end_min=p.end_min,
                )
                for p in operational_profile.phases
            ),
        )

        engine = ContextEngine()
        event_day_repo = _PreloadedEventDayRepository(event_day)
        profile_repo = _PreloadedOperationalProfileRepository(operational_profile)
        event_repo = _EmptyOperationalEventRepository()
        prediction_repo = _ReturnSavedPredictionRepository()

        generate_prediction = GeneratePrediction(
            engine=engine,
            event_day_repo=event_day_repo,
            operational_event_repo=event_repo,
            operational_profile_repo=profile_repo,
            prediction_repo=prediction_repo,
        )
        use_case = GetTerritorialPrediction(
            prediction_repo=prediction_repo,
            generate_prediction=generate_prediction,
        )

        prediction = await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
        )

        return prediction
