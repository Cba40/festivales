from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.entities.zone_behavior import ZoneBehavior


class ZoneBehaviorRepository(Protocol):
    async def find_by_zone_type_and_phase(
        self,
        zone_type_id: UUID,
        operational_phase_id: UUID,
    ) -> ZoneBehavior | None:
        ...
