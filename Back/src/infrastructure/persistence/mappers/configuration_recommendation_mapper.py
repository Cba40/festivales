from __future__ import annotations

from uuid import UUID

from src.domain.entities.configuration_recommendation import ConfigurationRecommendation
from src.domain.entities.recommendation_enums import RecommendationType, RecommendationStatus
from src.infrastructure.persistence.models.configuration_recommendation import ConfigurationRecommendation


def configuration_recommendation_to_domain(model: ConfigurationRecommendation) -> ConfigurationRecommendation:
    return ConfigurationRecommendation(
        id=model.id,
        target_entity_type=model.target_entity_type,
        target_entity_id=model.target_entity_id,
        proposed_change=model.proposed_change if model.proposed_change else None,
        recommendation_type=(
            RecommendationType(model.recommendation_type)
            if model.recommendation_type
            else None
        ),
        supporting_metrics=model.supporting_metrics if model.supporting_metrics else {},
        historic_trace=model.historic_trace if model.historic_trace else {},
        recommendation_confidence=model.recommendation_confidence,
        status=(
            RecommendationStatus(model.status) if model.status else RecommendationStatus.PENDING_REVIEW
        ),
        generated_at=model.generated_at,
        km_version_analyzed=model.km_version_analyzed,
        algorithm_version=model.algorithm_version,
        event_ids=model.event_ids if model.event_ids else None,
        resolved_by=model.resolved_by,
        resolved_at=model.resolved_at,
        resolution_justification=model.resolution_justification,
    )


def configuration_recommendation_to_model(entity: ConfigurationRecommendation) -> ConfigurationRecommendation:
    return ConfigurationRecommendation(
        id=entity.id,
        target_entity_type=entity.target_entity_type,
        target_entity_id=entity.target_entity_id,
        proposed_change=entity.proposed_change or "",
        recommendation_type=(
            entity.recommendation_type.value if entity.recommendation_type else None
        ),
        supporting_metrics=entity.supporting_metrics,
        historic_trace=entity.historic_trace,
        recommendation_confidence=entity.recommendation_confidence,
        status=entity.status.value if entity.status else "pending_review",
        generated_at=entity.generated_at,
        km_version_analyzed=entity.km_version_analyzed,
        algorithm_version=entity.algorithm_version,
        event_ids=entity.event_ids,
        resolved_by=entity.resolved_by,
        resolved_at=entity.resolved_at,
        resolution_justification=entity.resolution_justification,
    )