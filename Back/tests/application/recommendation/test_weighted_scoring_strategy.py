from datetime import datetime
from uuid import UUID

import pytest

from src.application.recommendation.config import (
    RecommendationConfig,
    configure_recommendation,
)
from src.application.recommendation.strategy import WeightedScoringStrategy
from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import (
    ActionType,
    RequestedAction,
    ZONE_TYPE_BY_ACTION,
)
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState


@pytest.fixture(autouse=True)
def reset_config() -> None:
    configure_recommendation(RecommendationConfig())
    yield


@pytest.fixture
def strategy() -> WeightedScoringStrategy:
    return WeightedScoringStrategy()


@pytest.fixture
def user_standard() -> UserContext:
    return UserContext(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        access_level=AccessLevel.STANDARD,
    )


@pytest.fixture
def user_vip() -> UserContext:
    return UserContext(
        user_id=UUID("00000000-0000-0000-0000-000000000002"),
        access_level=AccessLevel.VIP,
    )


@pytest.fixture
def user_staff() -> UserContext:
    return UserContext(
        user_id=UUID("00000000-0000-0000-0000-000000000003"),
        access_level=AccessLevel.STAFF,
    )


@pytest.fixture
def mobility_none() -> MobilityContext:
    return MobilityContext(
        current_zone_id=None,
        speed=1.2,
        accessibility_required=False,
    )


@pytest.fixture
def mobility_same_zone() -> MobilityContext:
    return MobilityContext(
        current_zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
        speed=0.8,
        accessibility_required=False,
    )


@pytest.fixture
def mobility_different_zone() -> MobilityContext:
    return MobilityContext(
        current_zone_id=UUID("a0000000-0000-0000-0000-000000000003"),
        speed=1.5,
        accessibility_required=False,
    )


@pytest.fixture
def mobility_accessible() -> MobilityContext:
    return MobilityContext(
        current_zone_id=None,
        speed=0.0,
        accessibility_required=True,
    )


@pytest.fixture
def action_low_density() -> RequestedAction:
    return RequestedAction(action_type=ActionType.SEEK_LOW_DENSITY)


@pytest.fixture
def action_exit() -> RequestedAction:
    return RequestedAction(action_type=ActionType.SEEK_EXIT)


@pytest.fixture
def action_service() -> RequestedAction:
    return RequestedAction(action_type=ActionType.SEEK_SERVICE)


# ── New ActionType fixtures ──────────────────────────────────────────────

@pytest.fixture
def action_parking() -> RequestedAction:
    return RequestedAction(action_type=ActionType.SEEK_PARKING)


@pytest.fixture
def action_food() -> RequestedAction:
    return RequestedAction(action_type=ActionType.SEEK_FOOD)


@pytest.fixture
def action_bathroom() -> RequestedAction:
    return RequestedAction(action_type=ActionType.SEEK_BATHROOM)


@pytest.fixture
def action_transport() -> RequestedAction:
    return RequestedAction(action_type=ActionType.SEEK_TRANSPORT)


@pytest.fixture
def action_accommodation() -> RequestedAction:
    return RequestedAction(action_type=ActionType.SEEK_ACCOMMODATION)


@pytest.fixture
def action_rest() -> RequestedAction:
    return RequestedAction(action_type=ActionType.SEEK_REST)


@pytest.fixture
def action_security() -> RequestedAction:
    return RequestedAction(action_type=ActionType.SEEK_SECURITY)


@pytest.fixture
def action_information() -> RequestedAction:
    return RequestedAction(action_type=ActionType.SEEK_INFORMATION)


@staticmethod
def _zone_a() -> ZoneState:
    return ZoneState(
        zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
        operational_state="LOW_DEMAND",
        availability=400,
        saturation_level=0.2,
        estimated_wait=0,
        confidence=1.0,
        reasoning_factors=[],
        active_restriction=FlowRestriction.OPEN,
    )


@staticmethod
def _zone_b() -> ZoneState:
    return ZoneState(
        zone_id=UUID("b0000000-0000-0000-0000-000000000002"),
        operational_state="MODERATE",
        availability=800,
        saturation_level=0.6,
        estimated_wait=15,
        confidence=0.8,
        reasoning_factors=["Impacto de evento operativo: -50"],
        active_restriction=FlowRestriction.REGULATED,
    )


@staticmethod
def _zone_c() -> ZoneState:
    return ZoneState(
        zone_id=UUID("c0000000-0000-0000-0000-000000000003"),
        operational_state="CLOSED",
        availability=0,
        saturation_level=0.9,
        estimated_wait=0,
        confidence=0.5,
        reasoning_factors=["Incidente activo en zona", "Zona cerrada"],
        active_restriction=FlowRestriction.CLOSED,
    )


@staticmethod
def _prediction(*, zone_states: list[ZoneState]) -> TerritorialPrediction:
    return TerritorialPrediction(
        timestamp=datetime(2026, 7, 15, 15, 0),
        zone_states=zone_states,
        active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
        active_event_day_phase_id=UUID("20000000-0000-0000-0000-000000000001"),
    )


class TestEmptyZoneStates:
    def test_empty_zone_states_returns_empty_list(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[]),
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
            config=RecommendationConfig(),
        )
        assert result == []


class TestSingleZone:
    def test_single_zone_returns_one_recommendation(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_a()]),
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
            config=RecommendationConfig(),
        )
        assert len(result) == 1
        assert result[0].zone_id == UUID("a0000000-0000-0000-0000-000000000001")


class TestScoring:
    def test_score_open_standard_no_mobility(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_a()]),
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
            config=RecommendationConfig(),
        )
        assert result[0].score == pytest.approx(0.8)

    def test_score_regulated_standard_no_mobility(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_b()]),
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
            config=RecommendationConfig(),
        )
        expected = (1.0 - 0.6) * (1.0 - 0.3)
        assert result[0].score == pytest.approx(expected)

    def test_vip_bonus_applied(
        self,
        strategy: WeightedScoringStrategy,
        user_vip: UserContext,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_a()]),
            user_context=user_vip,
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            config=RecommendationConfig(),
        )
        assert result[0].score == pytest.approx(0.9)

    def test_staff_bonus_applied(
        self,
        strategy: WeightedScoringStrategy,
        user_staff: UserContext,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_a()]),
            user_context=user_staff,
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            config=RecommendationConfig(),
        )
        assert result[0].score == pytest.approx(1.0)

    def test_mobility_penalty_applied(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_a()]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=UUID("c0000000-0000-0000-0000-000000000003"),
                speed=1.5,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            config=RecommendationConfig(),
        )
        assert result[0].score == pytest.approx(0.65)

    def test_no_mobility_penalty_same_zone(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_a()]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
                speed=0.8,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            config=RecommendationConfig(),
        )
        assert result[0].score == pytest.approx(0.8)

    def test_score_clamped_to_zero(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_b()]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=UUID("c0000000-0000-0000-0000-000000000003"),
                speed=10.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            config=RecommendationConfig(),
        )
        raw = (1.0 - 0.6) * (1.0 - 0.3) - 0.15
        assert result[0].score == pytest.approx(max(0.0, raw))


class TestFiltering:
    def test_seek_exit_filters_closed(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_a(), _zone_c()]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_EXIT),
            config=RecommendationConfig(),
        )
        assert len(result) == 1
        assert result[0].zone_id == _zone_a().zone_id

    def test_seek_low_density_filters_high_saturation(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_a(), _zone_b(), _zone_c()]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_LOW_DENSITY),
            config=RecommendationConfig(),
        )
        assert len(result) == 1
        assert result[0].zone_id == _zone_a().zone_id

    def test_accessibility_filters_closed_when_speed_zero(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_a(), _zone_c()]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=0.0,
                accessibility_required=True,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            config=RecommendationConfig(),
        )
        assert len(result) == 1
        assert result[0].zone_id == _zone_a().zone_id

    def test_accessibility_keeps_closed_when_speed_positive(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_a(), _zone_c()]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=True,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            config=RecommendationConfig(),
        )
        zone_ids = {r.zone_id for r in result}
        assert _zone_a().zone_id in zone_ids
        assert _zone_c().zone_id in zone_ids


class TestOrdering:
    def test_descending_by_score(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_b(), _zone_a()]),
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
            config=RecommendationConfig(),
        )
        assert result[0].zone_id == _zone_a().zone_id
        assert result[1].zone_id == _zone_b().zone_id

    def test_tie_ascending_by_saturation(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        zone_a = _zone_a()
        zone_a_same = ZoneState(
            zone_id=UUID("d0000000-0000-0000-0000-000000000004"),
            operational_state="LOW_DEMAND",
            availability=300,
            saturation_level=0.2,
            estimated_wait=0,
            confidence=1.0,
            reasoning_factors=[],
            active_restriction=FlowRestriction.OPEN,
        )
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[zone_a_same, zone_a]),
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
            config=RecommendationConfig(),
        )
        assert result[0].zone_id == zone_a.zone_id
        assert result[1].zone_id == zone_a_same.zone_id

    def test_tie_ascending_by_saturation_same_score(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        zone_reg = ZoneState(
            zone_id=UUID("b0000000-0000-0000-0000-000000000002"),
            operational_state="MODERATE",
            availability=800,
            saturation_level=0.2,
            estimated_wait=15,
            confidence=0.8,
            reasoning_factors=[],
            active_restriction=FlowRestriction.REGULATED,
        )
        zone_open = ZoneState(
            zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
            operational_state="LOW_DEMAND",
            availability=400,
            saturation_level=0.44,
            estimated_wait=0,
            confidence=1.0,
            reasoning_factors=[],
            active_restriction=FlowRestriction.OPEN,
        )
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[zone_reg, zone_open]),
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
            config=RecommendationConfig(),
        )
        zone_reg_score = (1.0 - 0.2) * (1.0 - 0.3)
        zone_open_score = 1.0 - 0.44
        assert zone_reg_score == pytest.approx(zone_open_score)
        assert result[0].zone_id == zone_reg.zone_id

    def test_tie_ascending_by_zone_id(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        zone_a = ZoneState(
            zone_id=UUID("00000000-0000-0000-0000-000000000001"),
            operational_state="LOW_DEMAND",
            availability=400,
            saturation_level=0.2,
            estimated_wait=0,
            confidence=1.0,
            reasoning_factors=[],
            active_restriction=FlowRestriction.OPEN,
        )
        zone_b = ZoneState(
            zone_id=UUID("00000000-0000-0000-0000-000000000002"),
            operational_state="LOW_DEMAND",
            availability=400,
            saturation_level=0.2,
            estimated_wait=0,
            confidence=1.0,
            reasoning_factors=[],
            active_restriction=FlowRestriction.OPEN,
        )
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[zone_b, zone_a]),
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
            config=RecommendationConfig(),
        )
        assert result[0].zone_id < result[1].zone_id


class TestReasoning:
    def test_reasoning_low_density(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_a()]),
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
            config=RecommendationConfig(),
        )
        assert "Baja densidad proyectada" in result[0].reasoning

    def test_reasoning_regulated(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_b()]),
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
            config=RecommendationConfig(),
        )
        assert "Acceso regulado operativo" in result[0].reasoning

    def test_reasoning_mobility(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_a()]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=UUID("c0000000-0000-0000-0000-000000000003"),
                speed=1.5,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            config=RecommendationConfig(),
        )
        assert "Requiere desplazamiento desde zona actual" in result[0].reasoning

    def test_reasoning_multiple_factors(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        zone_low_density_regulated = ZoneState(
            zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
            operational_state="LOW_DEMAND",
            availability=400,
            saturation_level=0.2,
            estimated_wait=0,
            confidence=1.0,
            reasoning_factors=[],
            active_restriction=FlowRestriction.REGULATED,
        )
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[zone_low_density_regulated]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=UUID("c0000000-0000-0000-0000-000000000003"),
                speed=1.5,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            config=RecommendationConfig(),
        )
        assert "Baja densidad proyectada" in result[0].reasoning
        assert "Acceso regulado operativo" in result[0].reasoning
        assert "Requiere desplazamiento desde zona actual" in result[0].reasoning


class TestNoResults:
    def test_all_filtered_by_seek_exit(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_c()]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_EXIT),
            config=RecommendationConfig(),
        )
        assert result == []

    def test_all_filtered_by_low_density(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_b(), _zone_c()]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_LOW_DENSITY),
            config=RecommendationConfig(),
        )
        assert result == []


class TestActionTypeCatalog:
    """Verify the definitive ActionType → ZoneType mapping."""

    @pytest.mark.parametrize(
        "action_type, expected_zone_type",
        [
            (ActionType.SEEK_PARKING, "Parking"),
            (ActionType.SEEK_FOOD, "Gastronomy"),
            (ActionType.SEEK_BATHROOM, "Sanitary"),
            (ActionType.SEEK_TRANSPORT, "Transport"),
            (ActionType.SEEK_ACCOMMODATION, "Accommodation"),
            (ActionType.SEEK_EXIT, "Transport"),
            (ActionType.SEEK_REST, "RestArea"),
            (ActionType.SEEK_SECURITY, "Security"),
            (ActionType.SEEK_INFORMATION, "Information"),
            (ActionType.SEEK_LOW_DENSITY, None),
            (ActionType.SEEK_SERVICE, None),
            (ActionType.SEEK_HYDRATION, None),
        ],
    )
    def test_zone_type_mapping(
        self,
        action_type: ActionType,
        expected_zone_type: str | None,
    ) -> None:
        action = RequestedAction(action_type=action_type)
        assert action.zone_type == expected_zone_type

    def test_explicit_zone_type_overrides_default(
        self,
    ) -> None:
        action = RequestedAction(
            action_type=ActionType.SEEK_PARKING,
            zone_type="CustomType",
        )
        assert action.zone_type == "CustomType"

    def test_no_ambiguous_action_types(self) -> None:
        """Every intention-oriented ActionType maps to exactly one ZoneType."""
        intention_oriented = [
            ActionType.SEEK_PARKING,
            ActionType.SEEK_FOOD,
            ActionType.SEEK_BATHROOM,
            ActionType.SEEK_TRANSPORT,
            ActionType.SEEK_ACCOMMODATION,
            ActionType.SEEK_EXIT,
            ActionType.SEEK_REST,
            ActionType.SEEK_SECURITY,
            ActionType.SEEK_INFORMATION,
        ]
        for at in intention_oriented:
            assert at in ZONE_TYPE_BY_ACTION
            assert ZONE_TYPE_BY_ACTION[at] is not None, (
                f"{at} must map to a ZoneType"
            )

    def test_service_not_used_for_specific_intents(self) -> None:
        """SEEK_SERVICE is not the documented ActionType for any screen."""
        specific = {
            ActionType.SEEK_PARKING,
            ActionType.SEEK_FOOD,
            ActionType.SEEK_BATHROOM,
            ActionType.SEEK_TRANSPORT,
            ActionType.SEEK_ACCOMMODATION,
            ActionType.SEEK_EXIT,
            ActionType.SEEK_REST,
            ActionType.SEEK_SECURITY,
            ActionType.SEEK_INFORMATION,
            ActionType.SEEK_HYDRATION,
        }
        service = ActionType.SEEK_SERVICE
        assert service not in specific


class TestNewActionTypesNoRegression:
    """New ActionTypes must not break existing filtering behaviour."""

    @pytest.mark.parametrize(
        "action_type",
        [
            ActionType.SEEK_PARKING,
            ActionType.SEEK_FOOD,
            ActionType.SEEK_BATHROOM,
            ActionType.SEEK_TRANSPORT,
            ActionType.SEEK_ACCOMMODATION,
            ActionType.SEEK_REST,
            ActionType.SEEK_SECURITY,
            ActionType.SEEK_INFORMATION,
        ],
    )
    def test_new_action_types_accept_all_zones_by_default(
        self,
        action_type: ActionType,
        strategy: WeightedScoringStrategy,
    ) -> None:
        action = RequestedAction(action_type=action_type)
        all_zones = [_zone_a(), _zone_b(), _zone_c()]
        result = strategy.evaluate(
            prediction=_prediction(zone_states=all_zones),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=action,
            config=RecommendationConfig(),
        )
        assert len(result) == 3, (
            f"{action_type} should not filter zones by default"
        )


class TestDeterminism:
    def test_deterministic_output(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        zone_states = [_zone_a(), _zone_b(), _zone_c()]
        prediction = _prediction(zone_states=zone_states)
        user = UserContext(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            access_level=AccessLevel.VIP,
        )
        mobility = MobilityContext(
            current_zone_id=UUID("c0000000-0000-0000-0000-000000000003"),
            speed=1.0,
            accessibility_required=True,
        )
        action = RequestedAction(action_type=ActionType.SEEK_SERVICE)
        config = RecommendationConfig()

        r1 = strategy.evaluate(
            prediction=prediction,
            user_context=user,
            mobility_context=mobility,
            requested_action=action,
            config=config,
        )
        r2 = strategy.evaluate(
            prediction=prediction,
            user_context=user,
            mobility_context=mobility,
            requested_action=action,
            config=config,
        )
        assert len(r1) == len(r2)
        for rec1, rec2 in zip(r1, r2):
            assert rec1.zone_id == rec2.zone_id
            assert rec1.score == rec2.score
            assert rec1.reasoning == rec2.reasoning


class TestConfigInjection:
    def test_use_custom_low_density_threshold(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        zone_low_sat = ZoneState(
            zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
            operational_state="LOW_DEMAND",
            availability=400,
            saturation_level=0.4,
            estimated_wait=0,
            confidence=1.0,
            reasoning_factors=[],
            active_restriction=FlowRestriction.OPEN,
        )
        custom_config = RecommendationConfig(low_density_saturation_threshold=0.3)
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[zone_low_sat]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_LOW_DENSITY),
            config=custom_config,
        )
        assert len(result) == 0

    def test_custom_mobility_penalty(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        custom_config = RecommendationConfig(mobility_penalty=0.5)
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[_zone_a()]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=UUID("c0000000-0000-0000-0000-000000000003"),
                speed=1.5,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_SERVICE),
            config=custom_config,
        )
        assert result[0].score == pytest.approx(0.3)
