from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.operational_observation import OperationalObservation
from src.domain.ports.operational_observation_repository import (
    OperationalObservationRepository,
)
from src.infrastructure.persistence.mappers import (
    operational_observation_to_domain,
    operational_observation_to_model,
)
from src.infrastructure.persistence.models import OperationalObservationModel


class SQLOperationalObservationRepository(OperationalObservationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, observation: OperationalObservation) -> OperationalObservation:
        model = operational_observation_to_model(observation)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return operational_observation_to_domain(model)

    async def find_by_id(self, id: UUID) -> OperationalObservation | None:
        model = await self._session.get(OperationalObservationModel, id)
        return operational_observation_to_domain(model) if model else None

    async def find_by_event_day(self, event_day_id: UUID) -> Sequence[OperationalObservation]:
        stmt = (
            select(OperationalObservationModel)
            .where(OperationalObservationModel.event_day_id == str(event_day_id))
            .order_by(OperationalObservationModel.timestamp)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [operational_observation_to_domain(m) for m in models]

    async def find_by_zone(self, zone_id: UUID) -> Sequence[OperationalObservation]:
        stmt = (
            select(OperationalObservationModel)
            .where(OperationalObservationModel.zone_id == str(zone_id))
            .order_by(OperationalObservationModel.timestamp)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [operational_observation_to_domain(m) for m in models]

    async def find_by_event_day_and_zone(
        self, event_day_id: UUID, zone_id: UUID
    ) -> Sequence[OperationalObservation]:
        stmt = (
            select(OperationalObservationModel)
            .where(
                OperationalObservationModel.event_day_id == str(event_day_id),
                OperationalObservationModel.zone_id == str(zone_id),
            )
            .order_by(OperationalObservationModel.timestamp)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [operational_observation_to_domain(m) for m in models]