from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.operational_event import OperationalEvent
from src.domain.ports.operational_event_repository import (
    OperationalEventRepository,
)
from src.infrastructure.persistence.mappers import (
    operational_event_to_domain,
)
from src.infrastructure.persistence.models import OperationalEventModel


class SQLOperationalEventRepository(OperationalEventRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_active_by_timestamp(
        self,
        timestamp: datetime,
    ) -> Sequence[OperationalEvent]:
        stmt = (
            select(OperationalEventModel)
            .where(
                OperationalEventModel.start_timestamp <= timestamp,
                OperationalEventModel.end_timestamp > timestamp,
            )
        )
        result = await self._session.execute(stmt)
        models = result.scalars().all()
        return [operational_event_to_domain(m) for m in models]
