from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.application.knowledge_model.snapshot_service import (
    get_or_create_current_version,
    KnowledgeModelSnapshotService,
)
from src.infrastructure.persistence.repositories.knowledge_model_version_repository import (
    SQLKnowledgeModelVersionRepository,
)


class KnowledgeModelSnapshotServiceImpl(KnowledgeModelSnapshotService):
    def __init__(self, repository: SQLKnowledgeModelVersionRepository) -> None:
        self._repository = repository

    async def get_or_create_current_version(
        self, created_by: str | None = None
    ) -> KnowledgeModelVersion:
        version = await self._repository.find_latest()
        if version is None:
            from uuid import uuid4
            version = KnowledgeModelVersion(
                id=uuid4(),
                version_number=1,
                snapshot_data={},
                created_at=datetime.now(),
                created_by=created_by,
            )
            await self._repository.save(version)
        return version