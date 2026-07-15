from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from src.domain.entities.event_day import EventDay
from src.domain.entities.zone_behavior import ZoneBehavior


class EventDayRepository(Protocol):
    def find_by_date(self, target_date: date) -> EventDay | None:
        ...


class ZoneBehaviorRepository(Protocol):
    def find_by_zone_type_and_phase(
        self, zone_type_id: UUID, operational_phase_id: UUID
    ) -> ZoneBehavior | None:
        ...
