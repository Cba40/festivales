from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from src.domain.entities.attendance_level import AttendanceLevel
from src.infrastructure.persistence.models.attendance_level import AttendanceLevelModel as AttendanceLevelORM


class SQLAttendanceLevelRepository:
    def __init__(self, session) -> None:
        self._session = session

    async def find_all(self):
        stmt = select(AttendanceLevelORM)
        result = await self._session.execute(stmt)
        return result.scalars().all()