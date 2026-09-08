from __future__ import annotations

from src.domain.entities.zone_recommendation import ZoneRecommendation
from src.infrastructure.persistence.models.zone_recommendation import (
    ZoneRecommendationModel,
)


def zone_recommendation_to_model(
    entity: ZoneRecommendation,
) -> ZoneRecommendationModel:
    return ZoneRecommendationModel(
        id=entity.id,
        event_day_id=entity.event_day_id,
        timestamp=entity.timestamp,
        zone_id=entity.zone_id,
        recommendation_type=entity.recommendation_type,
        score=entity.score,
        ranking=entity.ranking,
        reasoning=entity.reasoning,
        is_nearest=entity.is_nearest,
        metadata_json=entity.metadata,
    )


def zone_recommendation_to_domain(
    model: ZoneRecommendationModel,
) -> ZoneRecommendation:
    return ZoneRecommendation(
        id=model.id,
        event_day_id=model.event_day_id,
        timestamp=model.timestamp,
        zone_id=model.zone_id,
        recommendation_type=model.recommendation_type,
        score=model.score,
        ranking=model.ranking,
        reasoning=list(model.reasoning or []),
        is_nearest=bool(model.is_nearest),
        metadata=model.metadata_json,
    )