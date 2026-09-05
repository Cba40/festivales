from __future__ import annotations

from typing import Protocol

from uuid import UUID

from sqlalchemy import select

from src.domain.entities.knowledge_model_version import KnowledgeModelVersion
from src.domain.ports.knowledge_model_version_repository import KnowledgeModelVersionRepository
from src.infrastructure.persistence.models.knowledge_model_version import KnowledgeModelVersionModel


class SQLKnowledgeModelVersionRepository(KnowledgeModelVersionRepository):
    def __init__(self, session) -> None:
        self._session = session

    async def save(self, version: KnowledgeModelVersion) -> KnowledgeModelVersion:
        model = KnowledgeModelVersionModel(
            id=version.id,
            version_number=version.version_number,
            snapshot_data=version.snapshot_data,
            created_at=version.created_at,
            created_by=version.created_by,
        )
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return KnowledgeModelVersion(
            id=model.id,
            version_number=model.version_number,
            snapshot_data=model.snapshot_data,
            created_at=model.created_at,
            created_by=model.created_by,
        )

    async def find_by_id(self, id: UUID) -> KnowledgeModelVersion | None:
        stmt = select(KnowledgeModelVersionModel).where(KnowledgeModelVersionModel.id == id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return KnowledgeModelVersion(
            id=model.id,
            version_number=model.version_number,
            snapshot_data=model.snapshot_data,
            created_at=model.created_at,
            created_by=model.created_by,
        )

    async def find_latest(self) -> KnowledgeModelVersion | None:
        stmt = select(KnowledgeModelVersionModel).order_by(KnowledgeModelVersionModel.version_number.desc())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return KnowledgeModelVersion(
            id=model.id,
            version_number=model.version_number,
            snapshot_data=model.snapshot_data,
            created_at=model.created_at,
            created_by=model.created_by,
        )

    async def get_next_version_number(self) -> int:
        stmt = select(KnowledgeModelVersionModel.version_number).order_by(KnowledgeModelVersionModel.version_number.desc()).limit(1)
        result = await self._session.execute(stmt)
        row = result.first()
        if row is None:
            return 1
        return row[0] + 1