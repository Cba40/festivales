from __future__ import annotations

from datetime import date
from typing import Protocol

from src.domain.entities.event_day import EventDay


class EventDayRepository(Protocol):
    async def find_by_date(self, target_date: date) -> EventDay | None:
        ...
