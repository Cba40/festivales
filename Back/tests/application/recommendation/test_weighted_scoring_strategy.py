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
    OPERATIONAL_CLASSIFICATION_BY_ACTION,
    RequestedAction,
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
        zone_open = ZoneState(
            zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
            operational_state="LOW_DEMAND",
            availability=400,
            saturation_level=0.2,
            estimated_wait=0,
            confidence=1.0,
            reasoning_factors=[],
            active_restriction=FlowRestriction.OPEN,
            type="salida",
        )
        zone_closed = ZoneState(
            zone_id=UUID("c0000000-0000-0000-0000-000000000003"),
            operational_state="CLOSED",
            availability=0,
            saturation_level=0.9,
            estimated_wait=0,
            confidence=0.5,
            reasoning_factors=["Incidente activo en zona", "Zona cerrada"],
            active_restriction=FlowRestriction.CLOSED,
            type="salida",
        )
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[zone_open, zone_closed]),
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
        assert result[0].zone_id == zone_open.zone_id

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
        zone_closed = ZoneState(
            zone_id=UUID("c0000000-0000-0000-0000-000000000003"),
            operational_state="CLOSED",
            availability=0,
            saturation_level=0.9,
            estimated_wait=0,
            confidence=0.5,
            reasoning_factors=["Incidente activo en zona", "Zona cerrada"],
            active_restriction=FlowRestriction.CLOSED,
            type="salida",
        )
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[zone_closed]),
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
    """Verify the definitive ActionType → (type, subtipo) operational mapping."""

    @pytest.mark.parametrize(
        "action_type, expected_type, expected_subtipo",
        [
            (ActionType.SEEK_PARKING, "estacionamiento", None),
            (ActionType.SEEK_FOOD, "comida", None),
            (ActionType.SEEK_TRANSPORT, "transporte", None),
            (ActionType.SEEK_ACCOMMODATION, "hospedaje", None),
            (ActionType.SEEK_EXIT, "salida", None),
            (ActionType.SEEK_SECURITY, "emergencia", None),
            (ActionType.SEEK_BATHROOM, "servicios", "banos"),
            (ActionType.SEEK_HYDRATION, "servicios", "hidratacion"),
            (ActionType.SEEK_REST, "servicios", "descanso"),
            (ActionType.SEEK_HEALTH, "servicios", "salud"),
            (ActionType.SEEK_INFORMATION, None, None),
            (ActionType.SEEK_LOW_DENSITY, None, None),
            (ActionType.SEEK_SERVICE, None, None),
        ],
    )
    def test_operational_classification_mapping(
        self,
        action_type: ActionType,
        expected_type: str | None,
        expected_subtipo: str | None,
    ) -> None:
        action = RequestedAction(action_type=action_type)
        assert action.type == expected_type
        assert action.subtipo == expected_subtipo

    def test_zone_type_compat_exposes_operational_type(self) -> None:
        action = RequestedAction(action_type=ActionType.SEEK_PARKING)
        assert action.zone_type == "estacionamiento"

    def test_no_ambiguous_action_types(self) -> None:
        """Every intention-oriented ActionType maps to exactly one operational type."""
        intention_oriented = [
            ActionType.SEEK_PARKING,
            ActionType.SEEK_FOOD,
            ActionType.SEEK_BATHROOM,
            ActionType.SEEK_TRANSPORT,
            ActionType.SEEK_ACCOMMODATION,
            ActionType.SEEK_EXIT,
            ActionType.SEEK_REST,
            ActionType.SEEK_SECURITY,
            ActionType.SEEK_HEALTH,
        ]
        for at in intention_oriented:
            assert at in OPERATIONAL_CLASSIFICATION_BY_ACTION
            assert OPERATIONAL_CLASSIFICATION_BY_ACTION[at][0] is not None, (
                f"{at} must map to an operational type"
            )

    def test_unclassified_actions_have_no_type(self) -> None:
        """SEEK_INFORMATION and legacy actions carry no operational classification."""
        for at in (
            ActionType.SEEK_INFORMATION,
            ActionType.SEEK_LOW_DENSITY,
            ActionType.SEEK_SERVICE,
        ):
            action = RequestedAction(action_type=at)
            assert action.type is None
            assert action.subtipo is None

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
            ActionType.SEEK_HEALTH,
        }
        service = ActionType.SEEK_SERVICE
        assert service not in specific


class TestNewActionTypesNoRegression:
    """New ActionTypes must filter by operational classification (type/subtipo)."""

    @staticmethod
    def _typed_zone(
        *,
        zone_id: str,
        zone_type: str,
        subtipo: str | None = None,
        saturation_level: float = 0.2,
        active_restriction: FlowRestriction = FlowRestriction.OPEN,
    ) -> ZoneState:
        return ZoneState(
            zone_id=UUID(zone_id),
            operational_state="LOW_DEMAND",
            availability=400,
            saturation_level=saturation_level,
            estimated_wait=0,
            confidence=1.0,
            reasoning_factors=[],
            active_restriction=active_restriction,
            type=zone_type,
            subtipo=subtipo,
        )

    @pytest.mark.parametrize(
        "action_type, zone_type, subtipo",
        [
            (ActionType.SEEK_PARKING, "estacionamiento", None),
            (ActionType.SEEK_FOOD, "comida", None),
            (ActionType.SEEK_BATHROOM, "servicios", "banos"),
            (ActionType.SEEK_TRANSPORT, "transporte", None),
            (ActionType.SEEK_ACCOMMODATION, "hospedaje", None),
            (ActionType.SEEK_REST, "servicios", "descanso"),
            (ActionType.SEEK_SECURITY, "emergencia", None),
            (ActionType.SEEK_HYDRATION, "servicios", "hidratacion"),
            (ActionType.SEEK_HEALTH, "servicios", "salud"),
        ],
    )
    def test_new_action_types_filter_by_classification(
        self,
        action_type: ActionType,
        zone_type: str,
        subtipo: str | None,
        strategy: WeightedScoringStrategy,
    ) -> None:
        matching = self._typed_zone(
            zone_id="a0000000-0000-0000-0000-000000000001",
            zone_type=zone_type,
            subtipo=subtipo,
        )
        different = self._typed_zone(
            zone_id="c0000000-0000-0000-0000-000000000003",
            zone_type="salida",
            subtipo=None,
        )
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[matching, different]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=action_type),
            config=RecommendationConfig(),
        )
        assert len(result) == 1, (
            f"{action_type} should only keep zones of type={zone_type} "
            f"subtipo={subtipo}"
        )
        assert result[0].zone_id == matching.zone_id

    def test_subtipo_is_enforced_when_present(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        banos = self._typed_zone(
            zone_id="a0000000-0000-0000-0000-000000000001",
            zone_type="servicios",
            subtipo="banos",
        )
        descanso = self._typed_zone(
            zone_id="b0000000-0000-0000-0000-000000000002",
            zone_type="servicios",
            subtipo="descanso",
        )
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[banos, descanso]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_BATHROOM),
            config=RecommendationConfig(),
        )
        assert len(result) == 1
        assert result[0].zone_id == banos.zone_id

    def test_no_subtipo_matches_any_subtipo_of_the_type(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        parking_plain = self._typed_zone(
            zone_id="a0000000-0000-0000-0000-000000000001",
            zone_type="estacionamiento",
            subtipo=None,
        )
        parking_extra = self._typed_zone(
            zone_id="b0000000-0000-0000-0000-000000000002",
            zone_type="estacionamiento",
            subtipo="premium",
        )
        result = strategy.evaluate(
            prediction=_prediction(zone_states=[parking_plain, parking_extra]),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_PARKING),
            config=RecommendationConfig(),
        )
        assert len(result) == 2

    def test_type_none_applies_no_classification_filter(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        zones = [
            self._typed_zone(
                zone_id="a0000000-0000-0000-0000-000000000001",
                zone_type="comida",
            ),
            self._typed_zone(
                zone_id="b0000000-0000-0000-0000-000000000002",
                zone_type="servicios",
                subtipo="banos",
            ),
        ]
        result = strategy.evaluate(
            prediction=_prediction(zone_states=zones),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_INFORMATION),
            config=RecommendationConfig(),
        )
        assert len(result) == 2

    def test_all_filtered_when_no_zone_matches_classification(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        result = strategy.evaluate(
            prediction=_prediction(
                zone_states=[
                    self._typed_zone(
                        zone_id="a0000000-0000-0000-0000-000000000001",
                        zone_type="comida",
                    ),
                ]
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
            requested_action=RequestedAction(action_type=ActionType.SEEK_PARKING),
            config=RecommendationConfig(),
        )
        assert result == []


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


class TestNoSaturationSignal:
    """Cuando NO existe `saturation_level` (sin modelo especializado) no se
    fabrica una señal de saturación (ADR-004, Opción 3)."""

    @staticmethod
    def _zone_without_saturation(
        active_restriction: FlowRestriction = FlowRestriction.OPEN,
        type: str | None = None,
        subtipo: str | None = None,
    ) -> ZoneState:
        return ZoneState(
            zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
            operational_state="LOW_DEMAND",
            reasoning_factors=[],
            active_restriction=active_restriction,
            type=type,
            subtipo=subtipo,
        )

    def _evaluate(
        self,
        strategy: WeightedScoringStrategy,
        zone_states: list[ZoneState],
        action: ActionType,
        rescue_config: RecommendationConfig | None = None,
    ) -> list[ZoneRecommendation]:
        return strategy.evaluate(
            prediction=_prediction(zone_states=zone_states),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.0,
                accessibility_required=False,
            ),
            requested_action=RequestedAction(action_type=action),
            config=rescue_config or RecommendationConfig(),
        )

    def test_absence_of_saturation_does_not_force_score_one(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        # Regulada y sin saturación: no hay término de densidad, pero SÍ aplican
        # las demás componentes (penalización por restricción). El score no es 1.0.
        result = self._evaluate(
            strategy,
            [self._zone_without_saturation(FlowRestriction.REGULATED)],
            ActionType.SEEK_SERVICE,
        )
        assert result[0].score == pytest.approx(1.0 * (1.0 - 0.3))
        assert result[0].score != pytest.approx(1.0)

    def test_no_density_penalty_nor_bonus_without_saturation(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        # Abierta sin saturación: sin término de densidad, base 1.0 sin
        # penalización/bonus derivados de densidad.
        result = self._evaluate(
            strategy,
            [self._zone_without_saturation()],
            ActionType.SEEK_SERVICE,
        )
        assert result[0].score == pytest.approx(1.0)

    def test_present_saturation_still_uses_density_term(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        # Con saturación presente el comportamiento se mantiene: 1.0 - saturación.
        zone = ZoneState(
            zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
            operational_state="LOW_DEMAND",
            saturation_level=0.2,
            reasoning_factors=[],
            active_restriction=FlowRestriction.OPEN,
        )
        result = self._evaluate(strategy, [zone], ActionType.SEEK_SERVICE)
        assert result[0].score == pytest.approx(1.0 - 0.2)

    def test_seek_low_density_does_not_filter_without_saturation(
        self,
        strategy: WeightedScoringStrategy,
    ) -> None:
        # Sin saturación no se aplica el filtro de baja densidad (Opción 3);
        # ambas zonas siguen siendo elegibles.
        zona_a = self._zone_without_saturation(type="comida")
        zona_b = ZoneState(
            zone_id=UUID("b0000000-0000-0000-0000-000000000002"),
            operational_state="LOW_DEMAND",
            reasoning_factors=[],
            active_restriction=FlowRestriction.OPEN,
            type="servicios",
        )
        result = self._evaluate(
            strategy, [zona_a, zona_b], ActionType.SEEK_LOW_DENSITY
        )
        assert len(result) == 2
