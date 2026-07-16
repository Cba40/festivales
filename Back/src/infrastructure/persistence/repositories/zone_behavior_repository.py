from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.zone_behavior import ZoneBehavior
from src.domain.ports.zone_behavior_repository import ZoneBehaviorRepository
from src.infrastructure.persistence.mappers import zone_behavior_to_domain
from src.infrastructure.persistence.models import ZoneBehaviorModel


class SQLZoneBehaviorRepository(ZoneBehaviorRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_zone_type_and_phase(
        self,
        zone_type_id: UUID,
        operational_phase_id: UUID,
    ) -> ZoneBehavior | None:
        stmt = (
            select(ZoneBehaviorModel)
            .where(ZoneBehaviorModel.zone_type_id == zone_type_id)
            .where(ZoneBehaviorModel.operational_phase_id == operational_phase_id)
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return zone_behavior_to_domain(model)
