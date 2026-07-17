from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.infrastructure.persistence.repositories import (
    SQLEventDayRepository,
)


async def seed_event_day(
    session: AsyncSession,
    event_date: date,
    operational_profile_id: UUID,
    attendance_level_id: UUID,
    operational_start_min: int,
    operational_end_min: int,
    phases: list[tuple[UUID, int, int]],
) -> EventDay:
    repo = SQLEventDayRepository(session)

    event_day_id = uuid4()
    phase_entities = tuple(
        EventDayPhase(
            id=uuid4(),
            event_day_id=event_day_id,
            operational_phase_id=pid,
            start_min=sm,
            end_min=em,
        )
        for pid, sm, em in phases
    )

    event_day = EventDay(
        id=event_day_id,
        event_date=event_date,
        operational_profile_id=operational_profile_id,
        attendance_level_id=attendance_level_id,
        operational_start_min=operational_start_min,
        operational_end_min=operational_end_min,
        phases=phase_entities,
    )

    return await repo.save(event_day)
