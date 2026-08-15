from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from src.application.recommendation.config import (
    RecommendationConfig,
    get_recommendation_config,
)
from src.application.recommendation.strategy import (
    RecommendationStrategy,
    WeightedScoringStrategy,
)
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import RequestedAction
from src.domain.recommendation.user_context import UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction


class RecommendationService:
    def __init__(self, strategy: RecommendationStrategy | None = None) -> None:
        self._strategy = strategy if strategy is not None else WeightedScoringStrategy()

    def recommend(
        self,
        *,
        prediction: TerritorialPrediction,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
        limit: int = 5,
        config: RecommendationConfig | None = None,
        zone_coordinates: Mapping[UUID, tuple[float, float]] | None = None,
    ) -> list[ZoneRecommendation]:
        resolved_config = config if config is not None else get_recommendation_config()

        if limit == 0:
            return []

        evaluate_kwargs: dict[str, object] = {
            "prediction": prediction,
            "user_context": user_context,
            "mobility_context": mobility_context,
            "requested_action": requested_action,
            "config": resolved_config,
        }
        if zone_coordinates is not None:
            evaluate_kwargs["zone_coordinates"] = zone_coordinates

        recommendations = self._strategy.evaluate(**evaluate_kwargs)

        return recommendations[:limit]
