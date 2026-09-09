from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID

from src.application.context_engine import ContextEngine
from src.application.context_engine.exceptions import (
    DomainNotConfigured,
)
from src.application.context_engine.stage1_context_resolution import (
    resolve_active_event_day,
)
from src.application.context_engine.stage4_config import Stage4Config
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import ZoneBehavior
from src.domain.ports import (
    EventDayRepository,
    OperationalEventRepository,
    PredictionRepository,
)
from src.domain.value_objects.territorial_prediction import TerritorialPrediction


class GeneratePrediction:
    def __init__(
        self,
        engine: ContextEngine,
        event_day_repo: EventDayRepository,
        operational_event_repo: OperationalEventRepository,
        prediction_repo: PredictionRepository,
    ) -> None:
        self._engine = engine
        self._event_day_repo = event_day_repo
        self._operational_event_repo = operational_event_repo
        self._prediction_repo = prediction_repo

    async def execute(
        self,
        timestamp: datetime,
        zones: Sequence[Zone],
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel | None,
        operational_phases: Mapping[UUID, OperationalPhase],
        knowledge_model_version_id: UUID | None = None,
        config: Stage4Config | None = None,
    ) -> TerritorialPrediction:
        event_day = await resolve_active_event_day(
            timestamp,
            self._event_day_repo.find_by_date,
        )
        if event_day is None:
            raise DomainNotConfigured(
                f"No EventDay configured for date {timestamp.date()}"
            )

        events = await self._operational_event_repo.find_active_by_timestamp(
            timestamp,
        )

        engine_kwargs: dict = {
            "timestamp": timestamp,
            "zones": zones,
            "zone_behaviors": zone_behaviors,
            "operational_phases": operational_phases,
            "attendance_level": attendance_level,
            "event_day": event_day,
            "events": events,
            "config": config,
        }
        if knowledge_model_version_id is not None:
            engine_kwargs["knowledge_model_version_id"] = knowledge_model_version_id

        prediction = self._engine.predict(**engine_kwargs)

        prediction = await self._prediction_repo.save(prediction)

        return prediction
