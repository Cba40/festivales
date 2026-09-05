from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from src.domain.entities.zone_type import ZoneType
from src.infrastructure.persistence.models.zone_type import ZoneTypeModel as ZoneTypeORM


class SQLZoneTypeRepository:
    def __init__(self, session) -> None:
        self._session = session

    async def find_all(self):
        stmt = select(ZoneTypeORM)
        result = await self._session.execute(stmt)
        return result.scalars().all()