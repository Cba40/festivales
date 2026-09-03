from datetime import datetime
from uuid import UUID

import pytest

from src.application.recommendation.config import RecommendationConfig
from src.application.recommendation.strategy import WeightedScoringStrategy
from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import ActionType, RequestedAction
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState

USER_LAT = 0.0
USER_LNG = 0.0


def _parking_zone(zone_id: str, saturation_level: float) -> ZoneState:
    return ZoneState(
        zone_id=UUID(zone_id),
        operational_state="LOW_DEMAND",
        availability=400,
        saturation_level=saturation_level,
        estimated_wait=0,
        confidence=1.0,
        reasoning_factors=[],
        active_restriction=FlowRestriction.OPEN,
        type="estacionamiento",
        subtipo=None,
    )


def _prediction(zone_states: list[ZoneState]) -> TerritorialPrediction:
    return TerritorialPrediction(
        timestamp=datetime(2026, 7, 15, 15, 0),
        zone_states=zone_states,
        active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
        active_event_day_phase_id=UUID("20000000-0000-0000-0000-000000000001"),
    )


def _evaluate(
    zone_states: list[ZoneState],
    zone_coordinates: dict[UUID, tuple[float, float]],
) -> list[ZoneRecommendation]:
    strategy = WeightedScoringStrategy()
    return strategy.evaluate(
        prediction=_prediction(zone_states),
        user_context=UserContext(
            user_id=UUID("00000000-0000-0000-0000-000000000001"),
            access_level=AccessLevel.STANDARD,
        ),
        mobility_context=MobilityContext(
            current_zone_id=None,
            speed=1.5,
            accessibility_required=False,
            latitude=USER_LAT,
            longitude=USER_LNG,
        ),
        requested_action=RequestedAction(action_type=ActionType.SEEK_PARKING),
        config=RecommendationConfig(),
        zone_coordinates=zone_coordinates,
    )


def _coords(*items: tuple[str, float]) -> dict[UUID, tuple[float, float]]:
    return {
        UUID(zone_id): (lat, USER_LNG)
        for zone_id, lat in items
    }


class TestThreeParkingOptions:
    def test_returns_three_options_ordered_by_availability_then_distance(
        self,
    ) -> None:
        a = _parking_zone("a0000000-0000-0000-0000-000000000001", 0.5)
        b = _parking_zone("b0000000-0000-0000-0000-000000000002", 0.1)
        c = _parking_zone("c0000000-0000-0000-0000-000000000003", 0.3)
        coords = _coords(
            ("a0000000-0000-0000-0000-000000000001", 0.05),
            ("b0000000-0000-0000-0000-000000000002", 0.02),
            ("c0000000-0000-0000-0000-000000000003", 0.002),
        )

        result = _evaluate([a, b, c], coords)

        assert len(result) == 3
        assert [r.zone_id for r in result] == [
            UUID("b0000000-0000-0000-0000-000000000002"),
            UUID("c0000000-0000-0000-0000-000000000003"),
            UUID("a0000000-0000-0000-0000-000000000001"),
        ]
        assert "Más cerca de vos" in result[2].reasoning

    def test_excludes_zones_with_availability_at_or_below_threshold(
        self,
    ) -> None:
        b = _parking_zone("b0000000-0000-0000-0000-000000000002", 0.1)
        c = _parking_zone("c0000000-0000-0000-0000-000000000003", 0.3)
        d = _parking_zone("d0000000-0000-0000-0000-000000000004", 0.99)
        coords = _coords(
            ("b0000000-0000-0000-0000-000000000002", 0.02),
            ("c0000000-0000-0000-0000-000000000003", 0.002),
            ("d0000000-0000-0000-0000-000000000004", 0.001),
        )

        result = _evaluate([b, c, d], coords)

        zone_ids = {r.zone_id for r in result}
        assert UUID("d0000000-0000-0000-0000-000000000004") not in zone_ids
        assert len(result) == 2

    def test_respects_min_availability_threshold(self) -> None:
        e = _parking_zone("e0000000-0000-0000-0000-000000000005", 0.94)
        f = _parking_zone("f0000000-0000-0000-0000-000000000006", 0.96)
        coords = _coords(
            ("e0000000-0000-0000-0000-000000000005", 0.002),
            ("f0000000-0000-0000-0000-000000000006", 0.001),
        )

        result = _evaluate([e, f], coords)

        config = RecommendationConfig()
        assert config.min_availability_threshold == 0.05
        zone_ids = {r.zone_id for r in result}
        assert UUID("e0000000-0000-0000-0000-000000000005") in zone_ids
        assert UUID("f0000000-0000-0000-0000-000000000006") not in zone_ids
        assert len(result) == 1

    def test_deterministic_output(self) -> None:
        a = _parking_zone("a0000000-0000-0000-0000-000000000001", 0.5)
        b = _parking_zone("b0000000-0000-0000-0000-000000000002", 0.1)
        c = _parking_zone("c0000000-0000-0000-0000-000000000003", 0.3)
        coords = _coords(
            ("a0000000-0000-0000-0000-000000000001", 0.05),
            ("b0000000-0000-0000-0000-000000000002", 0.02),
            ("c0000000-0000-0000-0000-000000000003", 0.002),
        )

        first = _evaluate([a, b, c], coords)
        second = _evaluate([a, b, c], coords)

        assert [r.zone_id for r in first] == [r.zone_id for r in second]
        assert [r.score for r in first] == [r.score for r in second]

    def test_returns_two_when_only_two_available(self) -> None:
        a = _parking_zone("a0000000-0000-0000-0000-000000000001", 0.5)
        b = _parking_zone("b0000000-0000-0000-0000-000000000002", 0.1)
        coords = _coords(
            ("a0000000-0000-0000-0000-000000000001", 0.05),
            ("b0000000-0000-0000-0000-000000000002", 0.02),
        )

        result = _evaluate([a, b], coords)

        assert len(result) == 2
        assert [r.zone_id for r in result] == [
            UUID("b0000000-0000-0000-0000-000000000002"),
            UUID("a0000000-0000-0000-0000-000000000001"),
        ]

    def test_three_options_are_distinct_when_nearest_is_least_available(
        self,
    ) -> None:
        a = _parking_zone("a0000000-0000-0000-0000-000000000001", 0.94)
        b = _parking_zone("b0000000-0000-0000-0000-000000000002", 0.23)
        c = _parking_zone("c0000000-0000-0000-0000-000000000003", 0.40)
        coords = _coords(
            ("a0000000-0000-0000-0000-000000000001", 0.002),
            ("b0000000-0000-0000-0000-000000000002", 0.0135),
            ("c0000000-0000-0000-0000-000000000003", 0.045),
        )

        result = _evaluate([a, b, c], coords)

        zone_ids = [r.zone_id for r in result]
        assert len(zone_ids) == len(set(zone_ids))
        # a es la más cercana al usuario (lat 0.002): entra como opción 2
        # (mejor balance disponibilidad/cercanía). El orden es [b, a, c].
        assert zone_ids[0] == UUID("b0000000-0000-0000-0000-000000000002")
        assert zone_ids[1] == UUID("a0000000-0000-0000-0000-000000000001")
        assert zone_ids[2] == UUID("c0000000-0000-0000-0000-000000000003")
        assert "Mejor balance de disponibilidad y cercanía" in result[1].reasoning
        assert "Más cerca de vos" in result[2].reasoning


class TestServiceNearest:
    """is_nearest en servicios — mismo patrón que Parking V1.

    Sin lat/lng del usuario → ninguna zona marcada. Con lat/lng → se marca
    únicamente la zona de menor distancia real (Haversine) al usuario.
    """

    def _service_zone(
        self,
        zone_id: str,
        saturation_level: float,
        subtipo: str = "banos",
    ) -> ZoneState:
        return ZoneState(
            zone_id=UUID(zone_id),
            operational_state="LOW_DEMAND",
            availability=400,
            saturation_level=saturation_level,
            estimated_wait=0,
            confidence=1.0,
            reasoning_factors=[],
            active_restriction=FlowRestriction.OPEN,
            type="servicios",
            subtipo=subtipo,
        )

    def _evaluate_service(
        self,
        zone_states: list[ZoneState],
        zone_coordinates: dict[UUID, tuple[float, float]],
        action: ActionType = ActionType.SEEK_BATHROOM,
        latitude: float | None = USER_LAT,
        longitude: float | None = USER_LNG,
    ) -> list[ZoneRecommendation]:
        strategy = WeightedScoringStrategy()
        return strategy.evaluate(
            prediction=_prediction(zone_states),
            user_context=UserContext(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                access_level=AccessLevel.STANDARD,
            ),
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.5,
                accessibility_required=False,
                latitude=latitude,
                longitude=longitude,
            ),
            requested_action=RequestedAction(action_type=action),
            config=RecommendationConfig(),
            zone_coordinates=zone_coordinates,
        )

    def test_service_marks_nearest_zone_when_coordinates_sent(self) -> None:
        a = self._service_zone("a0000000-0000-0000-0000-000000000001", 0.5)
        b = self._service_zone("b0000000-0000-0000-0000-000000000002", 0.1)
        c = self._service_zone("c0000000-0000-0000-0000-000000000003", 0.3)
        coords = _coords(
            ("a0000000-0000-0000-0000-000000000001", 0.05),
            ("b0000000-0000-0000-0000-000000000002", 0.02),
            ("c0000000-0000-0000-0000-000000000003", 0.002),
        )

        result = self._evaluate_service([a, b, c], coords)

        nearest = [r for r in result if r.is_nearest]
        assert len(nearest) == 1
        # c es la más cercana al usuario (lat 0.002 vs 0.0)
        assert nearest[0].zone_id == UUID(
            "c0000000-0000-0000-0000-000000000003"
        )

    def test_service_marks_nearest_for_each_subtipo(self) -> None:
        a = self._service_zone(
            "a0000000-0000-0000-0000-000000000001", 0.5, subtipo="hidratacion"
        )
        b = self._service_zone(
            "b0000000-0000-0000-0000-000000000002", 0.1, subtipo="hidratacion"
        )
        coords = _coords(
            ("a0000000-0000-0000-0000-000000000001", 0.05),
            ("b0000000-0000-0000-0000-000000000002", 0.002),
        )

        result = self._evaluate_service(
            [a, b],
            coords,
            action=ActionType.SEEK_HYDRATION,
        )

        nearest = [r for r in result if r.is_nearest]
        assert len(nearest) == 1
        assert nearest[0].zone_id == UUID(
            "b0000000-0000-0000-0000-000000000002"
        )

    def test_service_no_coordinates_marks_none(self) -> None:
        a = self._service_zone("a0000000-0000-0000-0000-000000000001", 0.5)
        b = self._service_zone("b0000000-0000-0000-0000-000000000002", 0.1)
        coords = _coords(
            ("a0000000-0000-0000-0000-000000000001", 0.05),
            ("b0000000-0000-0000-0000-000000000002", 0.002),
        )

        result = self._evaluate_service(
            [a, b], coords, latitude=None, longitude=None
        )

        assert all(r.is_nearest is False for r in result)

    def test_service_zone_without_coordinates_is_not_marked(self) -> None:
        a = self._service_zone("a0000000-0000-0000-0000-000000000001", 0.5)
        b = self._service_zone("b0000000-0000-0000-0000-000000000002", 0.1)
        # b no tiene coordenadas en el mapping
        coords = _coords(("a0000000-0000-0000-0000-000000000001", 0.05))

        result = self._evaluate_service([a, b], coords)

        by_id = {r.zone_id: r.is_nearest for r in result}
        assert by_id[UUID("a0000000-0000-0000-0000-000000000001")] is True
        assert by_id[UUID("b0000000-0000-0000-0000-000000000002")] is False