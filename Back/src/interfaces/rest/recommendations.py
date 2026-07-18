"""REST adapter: thin bridge between the HTTP route and RecommendationModule."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import RequestedAction
from src.domain.recommendation.user_context import UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.infrastructure.composition.recommendation_module import RecommendationModule


async def get_recommendations_adapter(
    db: AsyncSession,
    *,
    timestamp: datetime,
    event_id: str,
    user_context: UserContext,
    mobility_context: MobilityContext,
    requested_action: RequestedAction,
    limit: int = 5,
) -> tuple[list[ZoneRecommendation], TerritorialPrediction | None]:
    module = RecommendationModule(db=db)
    return await module.execute(
        timestamp=timestamp,
        event_id=event_id,
        user_context=user_context,
        mobility_context=mobility_context,
        requested_action=requested_action,
        limit=limit,
    )
