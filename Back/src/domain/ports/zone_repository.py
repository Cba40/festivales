from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.domain.entities.zone import Zone


class ZoneRepository(Protocol):
    async def find_by_id(self, zone_id: UUID) -> Zone | None:
        ...

    async def find_all(self) -> Sequence[Zone]:
        ...

    async def save(self, zone: Zone) -> Zone:
        ...
