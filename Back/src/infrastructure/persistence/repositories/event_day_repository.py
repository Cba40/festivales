from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.event_day import EventDay
from src.domain.ports.event_day_repository import EventDayRepository
from src.infrastructure.persistence.mappers import (
    event_day_to_domain,
    event_day_to_model,
)
from src.infrastructure.persistence.models import EventDayModel, EventDayPhaseModel


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

    async def save(self, event_day: EventDay) -> EventDay:
        existing = await self._session.get(
            EventDayModel,
            event_day.id,
            options=[selectinload(EventDayModel.phases)],
        )

        if existing is not None:
            existing.event_date = event_day.event_date
            existing.operational_profile_id = event_day.operational_profile_id
            existing.attendance_level_id = event_day.attendance_level_id
            existing.operational_start_min = event_day.operational_start_min
            existing.operational_end_min = event_day.operational_end_min

            existing_phase_ids = {p.id for p in existing.phases}
            new_phase_ids = {p.id for p in event_day.phases}

            orphan_ids = existing_phase_ids - new_phase_ids
            if orphan_ids:
                existing.phases[:] = [
                    p for p in existing.phases if p.id not in orphan_ids
                ]
                for phase_id in orphan_ids:
                    orphan = await self._session.get(EventDayPhaseModel, phase_id)
                    if orphan is not None:
                        await self._session.delete(orphan)

            for phase in event_day.phases:
                if phase.id in existing_phase_ids:
                    phase_model = next(
                        p for p in existing.phases if p.id == phase.id
                    )
                    phase_model.operational_phase_id = phase.operational_phase_id
                    phase_model.start_min = phase.start_min
                    phase_model.end_min = phase.end_min
                else:
                    existing.phases.append(
                        EventDayPhaseModel(
                            id=phase.id,
                            event_day_id=event_day.id,
                            operational_phase_id=phase.operational_phase_id,
                            start_min=phase.start_min,
                            end_min=phase.end_min,
                        )
                    )

            await self._session.flush()
            await self._session.refresh(existing, attribute_names=["phases"])
            return event_day_to_domain(existing)
        else:
            model = event_day_to_model(event_day)
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model, attribute_names=["phases"])
            return event_day_to_domain(model)
