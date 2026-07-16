from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.event_day import EventDay
from src.domain.ports.event_day_repository import EventDayRepository
from src.infrastructure.persistence.mappers import event_day_to_domain
from src.infrastructure.persistence.models import EventDayModel


class SQLEventDayRepository(EventDayRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_date(self, target_date: date) -> EventDay | None:
        stmt = (
            select(EventDayModel)
            .where(EventDayModel.event_date == target_date)
            .options(selectinload(EventDayModel.phases))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return event_day_to_domain(model)
