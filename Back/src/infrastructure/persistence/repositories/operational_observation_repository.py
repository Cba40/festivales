from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.application.operational_observation.routes import SQLOperationalObservationRepository
from src.domain.entities.operational_observation import OperationalObservation
from src.domain.ports.operational_observation_repository import OperationalObservationRepository
from src.infrastructure.persistence.models import OperationalObservationModel
from src.infrastructure.persistence.mappers.operational_observation_mapper import observation_to_domain, observation_to_model


class SQLOperationalObservationRepository(OperationalObservationRepository):
    def __init__(self, session) -> None:
        self._session = session

    async def save(self, observation: OperationalObservation) -> OperationalObservation:
        model = observation_to_model(observation)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return observation_to_domain(model)

    async def find_by_zone_and_date_range(
        self,
        zone_id: str,
        start: datetime,
        end: datetime,
    ) -> list[OperationalObservation]:
        from sqlalchemy import select
        stmt = (
            select(OperationalObservationModel)
            .where(OperationalObservationModel.zone_id == zone_id)
            .where(OperationalObservationModel.timestamp >= start)
            .where(OperationalObservationModel.timestamp <= end)
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [observation_to_domain(m) for m in models]