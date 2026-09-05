from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.domain.entities.operational_observation import OperationalObservation


class OperationalObservationRepository(Protocol):
    async def save(self, observation: OperationalObservation) -> OperationalObservation: ...

    async def find_by_id(self, id: UUID) -> OperationalObservation | None: ...

    async def find_by_event_day(self, event_day_id: UUID) -> Sequence[OperationalObservation]: ...

    async def find_by_zone(self, zone_id: UUID) -> Sequence[OperationalObservation]: ...

    async def find_by_event_day_and_zone(
        self, event_day_id: UUID, zone_id: UUID
    ) -> Sequence[OperationalObservation]: ...