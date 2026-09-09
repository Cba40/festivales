from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID

from src.application.context_engine.stage4_config import Stage4Config
from src.application.use_cases.generate_prediction import GeneratePrediction
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import ZoneBehavior
from src.domain.ports import PredictionRepository
from src.domain.value_objects.territorial_prediction import TerritorialPrediction


class GetTerritorialPrediction:
    def __init__(
        self,
        prediction_repo: PredictionRepository,
        generate_prediction: GeneratePrediction,
    ) -> None:
        self._prediction_repo = prediction_repo
        self._generate_prediction = generate_prediction

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
        existing = await self._prediction_repo.find_by_timestamp(timestamp)
        if existing is not None:
            return existing

        generate_kwargs: dict = {
            "timestamp": timestamp,
            "zones": zones,
            "zone_behaviors": zone_behaviors,
            "attendance_level": attendance_level,
            "operational_phases": operational_phases,
            "config": config,
        }
        if knowledge_model_version_id is not None:
            generate_kwargs["knowledge_model_version_id"] = (
                knowledge_model_version_id
            )

        return await self._generate_prediction.execute(**generate_kwargs)
