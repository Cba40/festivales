from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.entities.operational_profile import OperationalProfile


class OperationalProfileRepository(Protocol):
    async def find_by_id(self, profile_id: UUID) -> OperationalProfile | None:
        ...

    async def save(self, profile: OperationalProfile) -> OperationalProfile:
        ...
