"""Tests for the corrections applied after the implementation audit."""
from __future__ import annotations

import logging
from datetime import datetime
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_async_db
from app.main import app
from src.application.recommendation.config import RecommendationConfig
from src.application.recommendation.strategy import WeightedScoringStrategy
from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import ActionType, RequestedAction
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState

EVENT_ID = "test-event-1"
BASE_URL = f"/api/events/{EVENT_ID}"
USER_LAT = 0.0
USER_LNG = 0.0


def _parking_zone(
    zone_id: str,
    saturation_level: float | None,
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


class TestCoordinateValidation:
    def test_out_of_range_latitude_returns_422(self) -> None:
        with patch(
            "app.api.routes.parking.get_parking_product_adapter",
            new_callable=AsyncMock,
        ):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(
                    f"{BASE_URL}/products/parking",
                    params={
                        "speed": 1.5,
                        "accessibility_required": False,
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "latitude": 95.0,
                        "longitude": 0.0,
                    },
                )

        assert resp.status_code == 422

    def test_out_of_range_longitude_returns_422(self) -> None:
        with patch(
            "app.api.routes.parking.get_parking_product_adapter",
            new_callable=AsyncMock,
        ):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(
                    f"{BASE_URL}/products/parking",
                    params={
                        "speed": 1.5,
                        "accessibility_required": False,
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "latitude": 0.0,
                        "longitude": 200.0,
                    },
                )

        assert resp.status_code == 422

    def test_bathroom_out_of_range_latitude_returns_422(self) -> None:
        with patch(
            "app.api.routes.bathroom.get_bathroom_product_adapter",
            new_callable=AsyncMock,
        ):
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get(
                    f"{BASE_URL}/products/bathroom",
                    params={
                        "speed": 1.5,
                        "accessibility_required": False,
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "latitude": 95.0,
                        "longitude": 0.0,
                    },
                )

        assert resp.status_code == 422

    def test_invalid_latitude_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            MobilityContext(
                current_zone_id=None,
                speed=1.5,
                accessibility_required=False,
                latitude=91.0,
                longitude=0.0,
            )

    def test_invalid_longitude_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            MobilityContext(
                current_zone_id=None,
                speed=1.5,
                accessibility_required=False,
                latitude=0.0,
                longitude=-181.0,
            )

    def test_valid_coordinates_do_not_raise(self) -> None:
        ctx = MobilityContext(
            current_zone_id=None,
            speed=1.5,
            accessibility_required=False,
            latitude=-30.97,
            longitude=-64.08,
        )
        assert ctx.latitude == -30.97
        assert ctx.longitude == -64.08


class TestIsNearest:
    def test_is_nearest_only_on_third_option(self) -> None:
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
        assert [r.is_nearest for r in result] == [False, False, True]

    def test_is_nearest_defaults_false_for_non_parking(self) -> None:
        rec = ZoneRecommendation(
            zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
            score=0.8,
            reasoning=["Razón"],
        )
        assert rec.is_nearest is False


class TestReasoning:
    def test_reasoning_includes_contextual_factors(self) -> None:
        b = _parking_zone("b0000000-0000-0000-0000-000000000002", 0.1)
        c = _parking_zone("c0000000-0000-0000-0000-000000000003", 0.3)
        coords = _coords(
            ("b0000000-0000-0000-0000-000000000002", 0.02),
            ("c0000000-0000-0000-0000-000000000003", 0.002),
        )

        result = _evaluate([b, c], coords)

        assert result[0].reasoning == [
            "Más lugares libres",
            "Baja densidad proyectada",
        ]
        assert result[1].reasoning[0] == "Segunda opción con más lugares"
        assert any("Baja densidad proyectada" in r.reasoning for r in result)


class TestMissingSaturationLevel:
    def test_zone_without_saturation_logs_warning_and_is_excluded(
        self,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        a = _parking_zone("a0000000-0000-0000-0000-000000000001", 0.3)
        b = _parking_zone("b0000000-0000-0000-0000-000000000002", None)
        coords = _coords(
            ("a0000000-0000-0000-0000-000000000001", 0.05),
            ("b0000000-0000-0000-0000-000000000002", 0.02),
        )

        with caplog.at_level(logging.WARNING):
            result = _evaluate([a, b], coords)

        assert len(result) == 1
        assert result[0].zone_id == UUID("a0000000-0000-0000-0000-000000000001")
        assert any(
            "saturation_level" in record.message
            and record.levelname == "WARNING"
            for record in caplog.records
        )