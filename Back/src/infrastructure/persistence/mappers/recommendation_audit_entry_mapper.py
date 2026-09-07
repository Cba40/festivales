from __future__ import annotations

from uuid import UUID

from src.domain.entities.recommendation_audit_entry import RecommendationAuditEntry
from src.infrastructure.persistence.models.recommendation_audit_entry import RecommendationAuditEntry


def recommendation_audit_entry_to_domain(model: RecommendationAuditEntry) -> RecommendationAuditEntry:
    return RecommendationAuditEntry(
        id=model.id,
        recommendation_id=model.recommendation_id,
        action=model.action,
        timestamp=model.timestamp,
        operator_id=model.operator_id,
        justification=model.justification,
        metrics_snapshot=model.metrics_snapshot if model.metrics_snapshot else {},
        input_data_snapshot=model.input_data_snapshot if model.input_data_snapshot else {},
        km_version=model.km_version,
        algorithm_version=model.algorithm_version,
        llm_version=model.llm_version,
    )


def recommendation_audit_entry_to_model(entity: RecommendationAuditEntry) -> RecommendationAuditEntry:
    return RecommendationAuditEntry(
        id=entity.id,
        recommendation_id=entity.recommendation_id,
        action=entity.action,
        timestamp=entity.timestamp,
        operator_id=entity.operator_id,
        justification=entity.justification,
        metrics_snapshot=entity.metrics_snapshot,
        input_data_snapshot=entity.input_data_snapshot,
        km_version=entity.km_version,
        algorithm_version=entity.algorithm_version,
        llm_version=entity.llm_version,
    )