from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.ports.prediction_repository import PredictionRepository
from src.infrastructure.persistence.mappers import (
    prediction_to_domain,
    prediction_to_model,
)
from src.infrastructure.persistence.models import PredictionModel


class SQLPredictionRepository(PredictionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self,
        prediction: TerritorialPrediction,
    ) -> TerritorialPrediction:
        model = prediction_to_model(prediction)
        self._session.add(model)
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(model)
        return prediction_to_domain(model)

    async def find_by_timestamp(
        self,
        timestamp: datetime,
    ) -> TerritorialPrediction | None:
        stmt = (
            select(PredictionModel)
            .where(PredictionModel.timestamp == timestamp)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return prediction_to_domain(model)

    async def find_by_event_day(
        self,
        event_day_id: UUID,
    ) -> list[TerritorialPrediction]:
        stmt = (
            select(PredictionModel)
            .where(PredictionModel.event_day_id == str(event_day_id))
            .order_by(PredictionModel.timestamp)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [prediction_to_domain(model) for model in models]
