"""REST adapter: thin bridge between the HTTP route and RecommendationModule."""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import RequestedAction
from src.domain.recommendation.user_context import UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.infrastructure.composition.recommendation_module import RecommendationModule

logger = logging.getLogger(__name__)


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
    recs, prediction = await module.execute(
        timestamp=timestamp,
        event_id=event_id,
        user_context=user_context,
        mobility_context=mobility_context,
        requested_action=requested_action,
        limit=limit,
    )

    logger.info(
        "[RECS_DEBUG] event=%s action_type=%s zone_type=%s recs_count=%s recs_zone_ids=[%s] prediction_zone_states=%s",
        event_id,
        requested_action.action_type.value,
        requested_action.zone_type,
        len(recs),
        ",".join(sorted(str(r.zone_id) for r in recs)),
        len(prediction.zone_states) if prediction is not None else 0,
    )
    if prediction is not None:
        pz_ids = sorted(str(zs.zone_id) for zs in prediction.zone_states)
        logger.info(
            "[RECS_DEBUG] event=%s prediction_zone_ids=[%s]",
            event_id,
            ",".join(pz_ids),
        )

    return recs, prediction
