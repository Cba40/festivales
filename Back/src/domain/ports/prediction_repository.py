from __future__ import annotations

from datetime import datetime
from typing import Protocol

from src.domain.value_objects.territorial_prediction import TerritorialPrediction


class PredictionRepository(Protocol):
    async def save(self, prediction: TerritorialPrediction) -> TerritorialPrediction:
        ...

    async def find_by_timestamp(
        self,
        timestamp: datetime,
    ) -> TerritorialPrediction | None:
        ...
