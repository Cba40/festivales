from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.entities.knowledge_model_version import KnowledgeModelVersion


class KnowledgeModelVersionRepository(Protocol):
    async def save(self, version: KnowledgeModelVersion) -> KnowledgeModelVersion:
        ...

    async def find_by_id(self, id: UUID) -> KnowledgeModelVersion | None:
        ...

    async def find_latest(self) -> KnowledgeModelVersion | None:
        ...

    async def get_next_version_number(self) -> int:
        ...