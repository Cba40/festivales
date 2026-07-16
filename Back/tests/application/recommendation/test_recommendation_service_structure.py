from uuid import UUID

import pytest

from src.application.recommendation.exceptions import (
    RecommendationNotPossible,
    RecommendationServiceError,
)
from src.application.recommendation.recommendation_service import (
    RecommendationService,
)
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import ActionType, RequestedAction
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.domain.entities.zone_behavior import FlowRestriction


@pytest.fixture
def user_context() -> UserContext:
    return UserContext(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        access_level=AccessLevel.STANDARD,
    )


@pytest.fixture
def mobility_context() -> MobilityContext:
    return MobilityContext(
        current_zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
        speed=1.2,
        accessibility_required=False,
    )


@pytest.fixture
def requested_action() -> RequestedAction:
    return RequestedAction(action_type=ActionType.SEEK_LOW_DENSITY)


@pytest.fixture
def prediction() -> TerritorialPrediction:
    zone_state = ZoneState(
        zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
        operational_state="LOW_DEMAND",
        availability=400,
        saturation_level=0.2,
        estimated_wait=0,
        confidence=1.0,
        reasoning_factors=["Baja densidad proyectada"],
        active_restriction=FlowRestriction.OPEN,
    )
    return TerritorialPrediction(
        timestamp=__import__("datetime").datetime(2026, 7, 15, 15, 0),
        zone_states=[zone_state],
        active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
        active_event_day_phase_id=UUID("20000000-0000-0000-0000-000000000001"),
    )


class TestRecommendationServiceCreation:
    def test_can_instantiate(self) -> None:
        service = RecommendationService()
        assert isinstance(service, RecommendationService)

    def test_recommend_method_exists(self) -> None:
        service = RecommendationService()
        assert hasattr(service, "recommend")
        assert callable(service.recommend)


class TestRecommendationServiceContract:
    def test_recommend_raises_not_implemented(
        self,
        prediction: TerritorialPrediction,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
    ) -> None:
        service = RecommendationService()
        with pytest.raises(NotImplementedError):
            service.recommend(
                prediction=prediction,
                user_context=user_context,
                mobility_context=mobility_context,
                requested_action=requested_action,
            )


class TestExceptions:
    def test_recommendation_service_error_is_exception(self) -> None:
        assert issubclass(RecommendationServiceError, Exception)

    def test_recommendation_not_possible(self) -> None:
        err = RecommendationNotPossible()
        assert "RECOMMENDATION_NOT_POSSIBLE" in str(err)

    def test_inheritance(self) -> None:
        assert issubclass(RecommendationNotPossible, RecommendationServiceError)


class TestValueObjects:
    def test_user_context_creation(self) -> None:
        ctx = UserContext(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            access_level=AccessLevel.VIP,
        )
        assert ctx.user_id == UUID("00000000-0000-0000-0000-000000000001")
        assert ctx.access_level == AccessLevel.VIP

    def test_mobility_context_creation(self) -> None:
        ctx = MobilityContext(
            current_zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
            speed=0.0,
            accessibility_required=True,
        )
        assert ctx.current_zone_id == UUID("a0000000-0000-0000-0000-000000000001")
        assert ctx.speed == 0.0
        assert ctx.accessibility_required is True

    def test_mobility_context_none_zone_id(self) -> None:
        ctx = MobilityContext(
            current_zone_id=None,
            speed=1.5,
            accessibility_required=False,
        )
        assert ctx.current_zone_id is None

    def test_requested_action_creation(self) -> None:
        action = RequestedAction(action_type=ActionType.SEEK_EXIT)
        assert action.action_type == ActionType.SEEK_EXIT

    def test_zone_recommendation_creation(self) -> None:
        rec = ZoneRecommendation(
            zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
            score=0.85,
            reasoning=["Baja densidad", "Acceso libre"],
        )
        assert rec.zone_id == UUID("a0000000-0000-0000-0000-000000000001")
        assert rec.score == 0.85
        assert rec.reasoning == ["Baja densidad", "Acceso libre"]

    def test_zone_recommendation_reasoning_copy_on_read(self) -> None:
        rec = ZoneRecommendation(
            zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
            score=0.5,
            reasoning=["test"],
        )
        reasoning = rec.reasoning
        reasoning.append("mutated")
        assert rec.reasoning == ["test"]

    def test_access_level_enum_values(self) -> None:
        assert AccessLevel.STANDARD.value == "STANDARD"
        assert AccessLevel.VIP.value == "VIP"
        assert AccessLevel.STAFF.value == "STAFF"

    def test_action_type_enum_values(self) -> None:
        assert ActionType.SEEK_LOW_DENSITY.value == "SEEK_LOW_DENSITY"
        assert ActionType.SEEK_EXIT.value == "SEEK_EXIT"
        assert ActionType.SEEK_SERVICE.value == "SEEK_SERVICE"
