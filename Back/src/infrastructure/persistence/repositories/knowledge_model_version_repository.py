from __future__ import annotations

from uuid import UUID

from src.application.knowledge_model.snapshot_service import KnowledgeModelSnapshotService
from src.domain.entities.knowledge_model_version import KnowledgeModelVersion
from src.domain.ports.knowledge_model_version_repository import KnowledgeModelVersionRepository
from src.infrastructure.persistence.models import KnowledgeModelVersionModel
from src.infrastructure.persistence.mappers.knowledge_model_version_mapper import km_version_to_domain, km_version_to_model


class SQLKnowledgeModelVersionRepository(KnowledgeModelVersionRepository):
    def __init__(self, session) -> None:
        self._session = session

    async def save(self, version: KnowledgeModelVersion) -> KnowledgeModelVersion:
        model = km_version_to_model(version)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return km_version_to_domain(model)

    async def find_latest(self) -> KnowledgeModelVersion | None:
        from sqlalchemy import select
        stmt = select(KnowledgeModelVersionModel).order_by(KnowledgeModelVersionModel.version_number.desc())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return km_version_to_domain(model)