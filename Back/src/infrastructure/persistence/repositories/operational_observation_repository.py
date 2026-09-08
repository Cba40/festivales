from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.operational_observation import OperationalObservation
from src.infrastructure.persistence.mappers.operational_observation_mapper import (
    observation_to_domain,
    observation_to_model,
)
from src.infrastructure.persistence.models import OperationalObservationModel


class SQLOperationalObservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, observation: OperationalObservation) -> OperationalObservation:
        model = observation_to_model(observation)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return observation_to_domain(model)

    async def find_by_id(self, id: UUID) -> OperationalObservation | None:
        model = await self._session.get(OperationalObservationModel, id)
        if model is None:
            return None
        return observation_to_domain(model)

    async def find_all(
        self,
        event_day_id: str | None = None,
        zone_id: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[OperationalObservation]:
        stmt = select(OperationalObservationModel)
        if event_day_id is not None:
            stmt = stmt.where(OperationalObservationModel.event_day_id == event_day_id)
        if zone_id is not None:
            stmt = stmt.where(OperationalObservationModel.zone_id == zone_id)
        if start_date is not None:
            stmt = stmt.where(OperationalObservationModel.timestamp >= start_date)
        if end_date is not None:
            stmt = stmt.where(OperationalObservationModel.timestamp <= end_date)
        stmt = stmt.order_by(OperationalObservationModel.timestamp)

        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [observation_to_domain(m) for m in models]