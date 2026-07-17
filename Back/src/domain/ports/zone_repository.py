from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.entities.zone import Zone


class ZoneRepository(Protocol):
    async def find_by_id(self, zone_id: UUID) -> Zone | None:
        ...

    async def save(self, zone: Zone) -> Zone:
        ...
