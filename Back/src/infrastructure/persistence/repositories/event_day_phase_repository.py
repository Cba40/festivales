from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from src.domain.entities.event_day_phase import EventDayPhase
from src.infrastructure.persistence.models.event_day_phase import EventDayPhaseModel as EventDayPhaseORM


class SQLEventDayPhaseRepository:
    def __init__(self, session) -> None:
        self._session = session

    async def find_all(self):
        stmt = select(EventDayPhaseORM)
        result = await self._session.execute(stmt)
        return result.scalars().all()