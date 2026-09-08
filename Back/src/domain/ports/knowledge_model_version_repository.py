from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.entities.knowledge_model_version import KnowledgeModelVersion


class KnowledgeModelVersionRepository(ABC):
    @abstractmethod
    async def save(self, version: KnowledgeModelVersion) -> KnowledgeModelVersion:
        raise NotImplementedError

    @abstractmethod
    async def find_latest(self) -> KnowledgeModelVersion | None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_snapshot_hash(self, snapshot_hash: str) -> KnowledgeModelVersion | None:
        raise NotImplementedError