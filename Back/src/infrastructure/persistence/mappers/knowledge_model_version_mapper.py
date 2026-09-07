from __future__ import annotations

from uuid import UUID

from src.domain.entities.knowledge_model_version import KnowledgeModelVersion
from src.infrastructure.persistence.models.knowledge_model_version import KnowledgeModelVersionModel


def km_version_to_model(entity: KnowledgeModelVersion) -> KnowledgeModelVersionModel:
    return KnowledgeModelVersionModel(
        id=entity.id,
        version_number=entity.version_number,
        snapshot_data=entity.snapshot_data,
        created_at=entity.created_at,
        created_by=entity.created_by,
    )


def km_version_to_domain(model: KnowledgeModelVersionModel) -> KnowledgeModelVersion:
    return KnowledgeModelVersion(
        id=model.id,
        version_number=model.version_number,
        snapshot_data=model.snapshot_data,
        created_at=model.created_at,
        created_by=model.created_by,
    )