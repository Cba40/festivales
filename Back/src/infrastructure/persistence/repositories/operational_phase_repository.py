from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from src.domain.entities.operational_phase import OperationalPhase
from src.infrastructure.persistence.models.operational_phase import OperationalPhaseModel as OperationalPhaseORM


class SQLOperationalPhaseRepository:
    def __init__(self, session) -> None:
        self._session = session

    async def find_all(self):
        stmt = select(OperationalPhaseORM)
        result = await self._session.execute(stmt)
        return result.scalars().all()