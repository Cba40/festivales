from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol

from src.domain.entities.operational_event import OperationalEvent


class OperationalEventRepository(Protocol):
    async def find_active_by_timestamp(
        self,
        timestamp: datetime,
    ) -> Sequence[OperationalEvent]:
        ...
