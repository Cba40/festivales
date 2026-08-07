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
    levels: dict[str, tuple[int, int | None]],
) -> list[AttendanceLevel]:
    result = await session.execute(select(AttendanceLevelModel.name))
    existing_names = {row[0] for row in result.fetchall()}

    created: list[AttendanceLevel] = []
    for name, (min_people, max_people) in levels.items():
        if name in existing_names:
            continue
        level = AttendanceLevel(
            id=uuid4(),
            name=name,
            min_people=min_people,
            max_people=max_people,
        )
        model = AttendanceLevelModel(
            id=level.id,
            name=level.name,
            min_people=level.min_people,
            max_people=level.max_people,
        )
        session.add(model)
        created.append(level)

    if created:
        await session.flush()
    return created