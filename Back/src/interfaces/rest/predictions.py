"""REST adapter: thin bridge between the HTTP route and PredictionModule."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.infrastructure.composition.prediction_module import PredictionModule


async def get_territorial_prediction_adapter(
    db: AsyncSession,
    *,
    timestamp: datetime,
    event_id: str,
) -> TerritorialPrediction | None:
    module = PredictionModule(db=db)
    return await module.execute(
        timestamp=timestamp,
        event_id=event_id,
    )
