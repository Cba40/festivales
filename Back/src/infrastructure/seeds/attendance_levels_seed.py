from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.attendance_level import AttendanceLevel
from src.infrastructure.persistence.models.attendance_level import (
    AttendanceLevelModel,
)


async def seed_attendance_levels(
    session: AsyncSession,
    multipliers: dict[str, float],
) -> list[AttendanceLevel]:
    result = await session.execute(select(AttendanceLevelModel.name))
    existing_names = {row[0] for row in result.fetchall()}

    created: list[AttendanceLevel] = []
    for name, multiplier in multipliers.items():
        if name in existing_names:
            continue
        level = AttendanceLevel(id=uuid4(), name=name, multiplier=multiplier)
        model = AttendanceLevelModel(id=level.id, name=level.name, multiplier=level.multiplier)
        session.add(model)
        created.append(level)

    if created:
        await session.flush()
    return created
