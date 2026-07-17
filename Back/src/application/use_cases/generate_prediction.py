from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID

from src.application.context_engine import ContextEngine
from src.application.context_engine.exceptions import (
    DomainNotConfigured,
    InvalidConfiguration,
)
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import ZoneBehavior
from src.domain.ports import (
    EventDayRepository,
    OperationalEventRepository,
    OperationalProfileRepository,
    PredictionRepository,
)
from src.domain.value_objects.territorial_prediction import TerritorialPrediction


class GeneratePrediction:
    def __init__(
        self,
        engine: ContextEngine,
        event_day_repo: EventDayRepository,
        operational_event_repo: OperationalEventRepository,
        operational_profile_repo: OperationalProfileRepository,
        prediction_repo: PredictionRepository,
    ) -> None:
        self._engine = engine
        self._event_day_repo = event_day_repo
        self._operational_event_repo = operational_event_repo
        self._operational_profile_repo = operational_profile_repo
        self._prediction_repo = prediction_repo

    async def execute(
        self,
        timestamp: datetime,
        zones: Sequence[Zone],
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> TerritorialPrediction:
        event_day = await self._event_day_repo.find_by_date(timestamp.date())
        if event_day is None:
            raise DomainNotConfigured(
                f"No EventDay configured for date {timestamp.date()}"
            )

        profile = await self._operational_profile_repo.find_by_id(
            event_day.operational_profile_id,
        )
        if profile is None:
            raise InvalidConfiguration(
                f"OperationalProfile {event_day.operational_profile_id} "
                f"referenced by EventDay {event_day.id} not found"
            )

        operational_phases = {p.id: p for p in profile.phases}

        events = await self._operational_event_repo.find_active_by_timestamp(
            timestamp,
        )

        prediction = self._engine.predict(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            operational_phases=operational_phases,
            attendance_level=attendance_level,
            event_day=event_day,
            events=events,
        )

        prediction = await self._prediction_repo.save(prediction)

        return prediction
