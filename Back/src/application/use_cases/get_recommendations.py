from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID

from src.application.recommendation.recommendation_service import (
    RecommendationService,
)
from src.application.use_cases.generate_prediction import GeneratePrediction
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import ZoneBehavior
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import RequestedAction
from src.domain.recommendation.user_context import UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation


class GetRecommendations:
    def __init__(
        self,
        generate_prediction: GeneratePrediction,
        recommendation_service: RecommendationService,
    ) -> None:
        self._generate_prediction = generate_prediction
        self._recommendation_service = recommendation_service

    async def execute(
        self,
        *,
        timestamp: datetime,
        zones: Sequence[Zone],
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
        limit: int = 5,
    ) -> list[ZoneRecommendation]:
        prediction = await self._generate_prediction.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
        )

        recommendations = self._recommendation_service.recommend(
            prediction=prediction,
            user_context=user_context,
            mobility_context=mobility_context,
            requested_action=requested_action,
            limit=limit,
        )

        return recommendations
