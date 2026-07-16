from datetime import datetime
from uuid import UUID

import pytest

from src.application.recommendation.config import (
    RecommendationConfig,
    configure_recommendation,
)
from src.application.recommendation.exceptions import (
    RecommendationNotPossible,
    RecommendationServiceError,
)
from src.application.recommendation.recommendation_service import (
    RecommendationService,
)
from src.application.recommendation.strategy import (
    RecommendationStrategy,
    WeightedScoringStrategy,
)
from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import ActionType, RequestedAction
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState


class FakeStrategy:
    def __init__(
        self, return_value: list[ZoneRecommendation] | None = None
    ) -> None:
        self._return_value = return_value if return_value is not None else []
        self.last_evaluate_call: dict | None = None

    def evaluate(
        self,
        *,
        prediction: TerritorialPrediction,
        user_context: UserContext,
        mobility_context: MobilityContext,
        requested_action: RequestedAction,
        config: RecommendationConfig,
    ) -> list[ZoneRecommendation]:
        self.last_evaluate_call = {
            "prediction": prediction,
            "user_context": user_context,
            "mobility_context": mobility_context,
            "requested_action": requested_action,
            "config": config,
        }
        return list(self._return_value)


@pytest.fixture(autouse=True)
def reset_config() -> None:
    configure_recommendation(RecommendationConfig())
    yield


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
        timestamp=datetime(2026, 7, 15, 15, 0),
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

    def test_default_strategy_is_weighted_scoring(self) -> None:
        service = RecommendationService()
        assert isinstance(service._strategy, WeightedScoringStrategy)


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


class TestDelegation:
    def test_delegates_to_strategy(self) -> None:
        fake = FakeStrategy(
            return_value=[
                ZoneRecommendation(
                    zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
                    score=0.8,
                    reasoning=["test"],
                ),
            ]
        )
        service = RecommendationService(strategy=fake)
        prediction = TerritorialPrediction(
            timestamp=datetime(2026, 7, 15, 15, 0),
            zone_states=[],
            active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
            active_event_day_phase_id=UUID("20000000-0000-0000-0000-000000000001"),
        )
        user = UserContext(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            access_level=AccessLevel.STANDARD,
        )
        mobility = MobilityContext(
            current_zone_id=None,
            speed=1.0,
            accessibility_required=False,
        )
        action = RequestedAction(action_type=ActionType.SEEK_SERVICE)
        config = RecommendationConfig()

        result = service.recommend(
            prediction=prediction,
            user_context=user,
            mobility_context=mobility,
            requested_action=action,
            limit=5,
            config=config,
        )
        assert fake.last_evaluate_call is not None
        assert fake.last_evaluate_call["prediction"] is prediction
        assert fake.last_evaluate_call["user_context"] is user
        assert fake.last_evaluate_call["mobility_context"] is mobility
        assert fake.last_evaluate_call["requested_action"] is action
        assert fake.last_evaluate_call["config"] is config
        assert len(result) == 1

    def test_returns_strategy_output_minus_limit(self) -> None:
        recs = [
            ZoneRecommendation(
                zone_id=UUID(f"00000000-0000-0000-0000-00000000000{i}"),
                score=0.8,
                reasoning=["test"],
            )
            for i in range(5)
        ]
        fake = FakeStrategy(return_value=recs)
        service = RecommendationService(strategy=fake)

        result = service.recommend(
            prediction=TerritorialPrediction(
                timestamp=datetime(2026, 7, 15, 15, 0),
                zone_states=[],
                active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
                active_event_day_phase_id=UUID("20000000-0000-0000-0000-000000000001"),
            ),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            limit=3,
        )
        assert len(result) == 3


class TestStrategyInjection:
    def test_custom_strategy_injected(self) -> None:
        fake = FakeStrategy()
        service = RecommendationService(strategy=fake)
        assert service._strategy is fake

    def test_strategy_protocol_satisfied_by_weighted_scoring(self) -> None:
        strategy: RecommendationStrategy = WeightedScoringStrategy()
        assert isinstance(strategy, RecommendationStrategy)

    def test_strategy_protocol_satisfied_by_fake(self) -> None:
        strategy: RecommendationStrategy = FakeStrategy()
        assert isinstance(strategy, RecommendationStrategy)


class TestLimit:
    def test_limit_zero_returns_empty(self) -> None:
        service = RecommendationService()
        result = service.recommend(
            prediction=TerritorialPrediction(
                timestamp=datetime(2026, 7, 15, 15, 0),
                zone_states=[],
                active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
                active_event_day_phase_id=UUID("20000000-0000-0000-0000-000000000001"),
            ),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            limit=0,
        )
        assert result == []

    def test_limit_zero_does_not_call_strategy(self) -> None:
        fake = FakeStrategy(
            return_value=[
                ZoneRecommendation(
                    zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
                    score=0.8,
                    reasoning=["test"],
                ),
            ]
        )
        service = RecommendationService(strategy=fake)
        service.recommend(
            prediction=TerritorialPrediction(
                timestamp=datetime(2026, 7, 15, 15, 0),
                zone_states=[],
                active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
                active_event_day_phase_id=UUID("20000000-0000-0000-0000-000000000001"),
            ),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            limit=0,
        )
        assert fake.last_evaluate_call is None

    def test_limit_truncates(self) -> None:
        recs = [
            ZoneRecommendation(
                zone_id=UUID(f"00000000-0000-0000-0000-00000000000{i}"),
                score=0.9,
                reasoning=["test"],
            )
            for i in range(5)
        ]
        fake = FakeStrategy(return_value=recs)
        service = RecommendationService(strategy=fake)

        result = service.recommend(
            prediction=TerritorialPrediction(
                timestamp=datetime(2026, 7, 15, 15, 0),
                zone_states=[],
                active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
                active_event_day_phase_id=UUID("20000000-0000-0000-0000-000000000001"),
            ),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            limit=3,
        )
        assert len(result) == 3

    def test_limit_above_count_returns_all(self) -> None:
        recs = [
            ZoneRecommendation(
                zone_id=UUID(f"00000000-0000-0000-0000-00000000000{i}"),
                score=0.9,
                reasoning=["test"],
            )
            for i in range(2)
        ]
        fake = FakeStrategy(return_value=recs)
        service = RecommendationService(strategy=fake)

        result = service.recommend(
            prediction=TerritorialPrediction(
                timestamp=datetime(2026, 7, 15, 15, 0),
                zone_states=[],
                active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
                active_event_day_phase_id=UUID("20000000-0000-0000-0000-000000000001"),
            ),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            limit=10,
        )
        assert len(result) == 2


class TestExceptionPropagation:
    def test_strategy_exception_propagates(self) -> None:
        class RaisesStrategy:
            def evaluate(
                self,
                **kwargs: object,
            ) -> list[ZoneRecommendation]:
                raise RuntimeError("strategy failed")

        service = RecommendationService(strategy=RaisesStrategy())
        with pytest.raises(RuntimeError, match="strategy failed"):
            service.recommend(
                prediction=TerritorialPrediction(
                    timestamp=datetime(2026, 7, 15, 15, 0),
                    zone_states=[],
                    active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
                    active_event_day_phase_id=UUID("20000000-0000-0000-0000-000000000001"),
                ),
                user_context=UserContext(
                    user_id=UUID("00000000-0000-0000-0000-000000000001"),
                    access_level=AccessLevel.STANDARD,
                ),
                mobility_context=MobilityContext(
                    current_zone_id=None,
                    speed=1.0,
                    accessibility_required=False,
                ),
                requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            )
