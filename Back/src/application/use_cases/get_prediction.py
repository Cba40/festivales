from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID

from src.application.use_cases.generate_prediction import GeneratePrediction
from src.domain.entities.attendance_level import AttendanceLevel
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
        attendance_level: AttendanceLevel,
    ) -> TerritorialPrediction:
        existing = await self._prediction_repo.find_by_timestamp(timestamp)
        if existing is not None:
            return existing

        return await self._generate_prediction.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
        )
