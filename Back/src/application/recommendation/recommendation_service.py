from __future__ import annotations

from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import RequestedAction
from src.domain.recommendation.user_context import UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction


class RecommendationService:
    def recommend(
        self,
        *,
        prediction: TerritorialPrediction,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
        limit: int = 5,
    ) -> list[ZoneRecommendation]:
        raise NotImplementedError(
            "Recommendation algorithm not yet implemented. "
            "Expected for T15.9."
        )
