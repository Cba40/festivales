from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from unittest.mock import ANY, AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.application.use_cases.get_recommendations import GetRecommendations
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction, ZoneBehavior
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import ActionType, RequestedAction
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction


@pytest.fixture
def timestamp() -> datetime:
    return datetime(2026, 1, 10, 20, 0)


@pytest.fixture
def zones() -> list[Zone]:
    return [
        Zone(
            id=UUID("a0000000-0000-0000-0000-000000000001"),
            name="Test Zone",
            zone_type_id=UUID("b0000000-0000-0000-0000-000000000001"),
            capacity=100,
        ),
    ]


@pytest.fixture
def zone_behaviors() -> dict[tuple[UUID, UUID], ZoneBehavior]:
    return {}


@pytest.fixture
def attendance_level() -> AttendanceLevel:
    return AttendanceLevel(
        id=UUID("50000000-0000-0000-0000-000000000001"),
        name="Normal",
        multiplier=1.0,
    )


@pytest.fixture
def user_context() -> UserContext:
    return UserContext(
        user_id=UUID("60000000-0000-0000-0000-000000000001"),
        access_level=AccessLevel.STANDARD,
    )


@pytest.fixture
def mobility_context() -> MobilityContext:
    return MobilityContext(
        current_zone_id=None,
        speed=1.0,
        accessibility_required=False,
    )


@pytest.fixture
def requested_action() -> RequestedAction:
    return RequestedAction(action_type=ActionType.SEEK_LOW_DENSITY)


@pytest.fixture
def prediction(timestamp: datetime) -> TerritorialPrediction:
    return TerritorialPrediction(
        timestamp=timestamp,
        zone_states=[],
        active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
        active_event_day_phase_id=UUID("30000000-0000-0000-0000-000000000001"),
    )


@pytest.fixture
def recommendations() -> list[ZoneRecommendation]:
    return [
        ZoneRecommendation(
            zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
            score=0.8,
            reasoning=["Baja densidad proyectada"],
        ),
    ]


@pytest.fixture
def generate_prediction(prediction: TerritorialPrediction) -> AsyncMock:
    gp = AsyncMock()
    gp.execute = AsyncMock(return_value=prediction)
    return gp


@pytest.fixture
def recommendation_service(
    recommendations: list[ZoneRecommendation],
) -> MagicMock:
    rs = MagicMock()
    rs.recommend = MagicMock(return_value=recommendations)
    return rs


@pytest.fixture
def use_case(
    generate_prediction: AsyncMock,
    recommendation_service: MagicMock,
) -> GetRecommendations:
    return GetRecommendations(
        generate_prediction=generate_prediction,
        recommendation_service=recommendation_service,
    )


class TestGetRecommendations:
    async def test_invokes_generate_prediction_once(
        self,
        use_case: GetRecommendations,
        generate_prediction: AsyncMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
    ) -> None:
        await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
            user_context=user_context,
            mobility_context=mobility_context,
            requested_action=requested_action,
        )

        generate_prediction.execute.assert_awaited_once()

    async def test_invokes_recommendation_service_once(
        self,
        use_case: GetRecommendations,
        recommendation_service: MagicMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
    ) -> None:
        await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
            user_context=user_context,
            mobility_context=mobility_context,
            requested_action=requested_action,
        )

        recommendation_service.recommend.assert_called_once()

    async def test_recommendation_receives_prediction_from_generate(
        self,
        use_case: GetRecommendations,
        generate_prediction: AsyncMock,
        recommendation_service: MagicMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
        prediction: TerritorialPrediction,
    ) -> None:
        await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
            user_context=user_context,
            mobility_context=mobility_context,
            requested_action=requested_action,
        )

        recommendation_service.recommend.assert_called_once_with(
            prediction=prediction,
            user_context=user_context,
            mobility_context=mobility_context,
            requested_action=requested_action,
            limit=5,
        )

    async def test_returns_recommendations_from_service(
        self,
        use_case: GetRecommendations,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
        recommendations: list[ZoneRecommendation],
    ) -> None:
        result = await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
            user_context=user_context,
            mobility_context=mobility_context,
            requested_action=requested_action,
        )

        assert result is recommendations

    async def test_does_not_recommend_when_generate_fails(
        self,
        use_case: GetRecommendations,
        generate_prediction: AsyncMock,
        recommendation_service: MagicMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
    ) -> None:
        generate_prediction.execute = AsyncMock(
            side_effect=RuntimeError("engine failure"),
        )

        with pytest.raises(RuntimeError):
            await use_case.execute(
                timestamp=timestamp,
                zones=zones,
                zone_behaviors=zone_behaviors,
                attendance_level=attendance_level,
                user_context=user_context,
                mobility_context=mobility_context,
                requested_action=requested_action,
            )

        recommendation_service.recommend.assert_not_called()

    async def test_propagates_recommendation_error(
        self,
        use_case: GetRecommendations,
        recommendation_service: MagicMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
    ) -> None:
        recommendation_service.recommend = MagicMock(
            side_effect=ValueError("recommendation failed"),
        )

        with pytest.raises(ValueError):
            await use_case.execute(
                timestamp=timestamp,
                zones=zones,
                zone_behaviors=zone_behaviors,
                attendance_level=attendance_level,
                user_context=user_context,
                mobility_context=mobility_context,
                requested_action=requested_action,
            )

    async def test_passes_custom_limit_to_recommendation(
        self,
        use_case: GetRecommendations,
        recommendation_service: MagicMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
    ) -> None:
        await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
            user_context=user_context,
            mobility_context=mobility_context,
            requested_action=requested_action,
            limit=3,
        )

        recommendation_service.recommend.assert_called_once_with(
            prediction=ANY,
            user_context=user_context,
            mobility_context=mobility_context,
            requested_action=requested_action,
            limit=3,
        )

    async def test_does_not_access_repositories(
        self,
        use_case: GetRecommendations,
        generate_prediction: AsyncMock,
        recommendation_service: MagicMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
    ) -> None:
        await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
            user_context=user_context,
            mobility_context=mobility_context,
            requested_action=requested_action,
        )

        assert generate_prediction.execute.await_count == 1
        assert recommendation_service.recommend.call_count == 1
