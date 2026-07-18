"""Tests for the GET /api/events/{event_id}/recommendations endpoint.

All DB access is mocked — only the route's HTTP contract is tested.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.db.session import get_async_db
from app.main import app
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction

EVENT_ID = "test-event-1"
BASE_URL = f"/api/events/{EVENT_ID}"


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_async_db():
    return AsyncMock()


@pytest.fixture(autouse=True)
def _override_get_async_db(mock_async_db):
    async def override():
        yield mock_async_db

    app.dependency_overrides[get_async_db] = override


@pytest.fixture
def auth_headers() -> dict[str, str]:
    expire = datetime.now(timezone.utc) + timedelta(hours=8)
    token = jwt.encode(
        {"sub": "admin", "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def sample_prediction() -> TerritorialPrediction:
    return TerritorialPrediction(
        timestamp=datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc),
        zone_states=[],
        active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
        active_event_day_phase_id=UUID("30000000-0000-0000-0000-000000000001"),
    )


@pytest.fixture
def sample_recommendations() -> list[ZoneRecommendation]:
    return [
        ZoneRecommendation(
            zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
            score=0.85,
            reasoning=["Baja densidad proyectada"],
        ),
        ZoneRecommendation(
            zone_id=UUID("a0000000-0000-0000-0000-000000000002"),
            score=0.62,
            reasoning=["Acceso regulado"],
        ),
    ]


@pytest.fixture(autouse=True)
def _mock_adapter(
    sample_recommendations: list[ZoneRecommendation],
    sample_prediction: TerritorialPrediction,
):
    with patch(
        "app.api.routes.recommendations.get_recommendations_adapter",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = (sample_recommendations, sample_prediction)
        yield mock


class TestRecommendationsEndpoint:
    def test_200_ok(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"{BASE_URL}/recommendations",
            params={
                "access_level": "STANDARD",
                "action_type": "SEEK_LOW_DENSITY",
                "speed": 1.5,
                "accessibility_required": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["event_id"] == EVENT_ID
        assert "timestamp" in body
        assert len(body["recommendations"]) == 2
        assert body["recommendations"][0]["zone_id"] == "a0000000-0000-0000-0000-000000000001"
        assert body["recommendations"][0]["score"] == 0.85

    def test_422_missing_required_params(self, client: TestClient, auth_headers: dict[str, str]):
        resp = client.get(
            f"{BASE_URL}/recommendations",
            params={"access_level": "STANDARD"},
            headers=auth_headers,
        )

        assert resp.status_code == 422

    def test_422_invalid_access_level(self, client: TestClient, auth_headers: dict[str, str]):
        resp = client.get(
            f"{BASE_URL}/recommendations",
            params={
                "access_level": "INVALID",
                "action_type": "SEEK_LOW_DENSITY",
                "speed": 1.5,
                "accessibility_required": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            },
            headers=auth_headers,
        )

        assert resp.status_code == 422

    def test_422_invalid_action_type(self, client: TestClient, auth_headers: dict[str, str]):
        resp = client.get(
            f"{BASE_URL}/recommendations",
            params={
                "access_level": "STANDARD",
                "action_type": "INVALID",
                "speed": 1.5,
                "accessibility_required": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            },
            headers=auth_headers,
        )

        assert resp.status_code == 422

    def test_422_negative_speed(self, client: TestClient, auth_headers: dict[str, str]):
        resp = client.get(
            f"{BASE_URL}/recommendations",
            params={
                "access_level": "STANDARD",
                "action_type": "SEEK_LOW_DENSITY",
                "speed": -1.0,
                "accessibility_required": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            },
            headers=auth_headers,
        )

        assert resp.status_code == 422

    def test_401_no_auth(self, client: TestClient):
        resp = client.get(
            f"{BASE_URL}/recommendations",
            params={
                "access_level": "STANDARD",
                "action_type": "SEEK_LOW_DENSITY",
                "speed": 1.5,
                "accessibility_required": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            },
        )

        assert resp.status_code == 401

    def test_500_prediction_failed(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
    ):
        _mock_adapter.return_value = ([], None)

        resp = client.get(
            f"{BASE_URL}/recommendations",
            params={
                "access_level": "STANDARD",
                "action_type": "SEEK_LOW_DENSITY",
                "speed": 1.5,
                "accessibility_required": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            },
            headers=auth_headers,
        )

        assert resp.status_code == 500

    def test_500_adapter_error(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
    ):
        _mock_adapter.side_effect = RuntimeError("engine failure")

        resp = client.get(
            f"{BASE_URL}/recommendations",
            params={
                "access_level": "STANDARD",
                "action_type": "SEEK_LOW_DENSITY",
                "speed": 1.5,
                "accessibility_required": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            },
            headers=auth_headers,
        )

        assert resp.status_code == 500

    def test_adapter_invoked_with_parsed_domain_params(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
    ):
        client.get(
            f"{BASE_URL}/recommendations",
            params={
                "access_level": "STANDARD",
                "action_type": "SEEK_LOW_DENSITY",
                "speed": 1.5,
                "accessibility_required": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            },
            headers=auth_headers,
        )

        _mock_adapter.assert_awaited_once()
        call_kwargs = _mock_adapter.await_args[1]

        assert call_kwargs["event_id"] == EVENT_ID
        assert call_kwargs["limit"] == 5

        user_ctx = call_kwargs["user_context"]
        assert user_ctx.access_level.value == "STANDARD"
        assert str(user_ctx.user_id) == "550e8400-e29b-41d4-a716-446655440000"

        mob_ctx = call_kwargs["mobility_context"]
        assert mob_ctx.speed == 1.5
        assert mob_ctx.accessibility_required is False
        assert mob_ctx.current_zone_id is None

        action = call_kwargs["requested_action"]
        assert action.action_type.value == "SEEK_LOW_DENSITY"

    def test_response_timestamp_from_prediction(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
        sample_prediction: TerritorialPrediction,
    ):
        resp = client.get(
            f"{BASE_URL}/recommendations",
            params={
                "access_level": "STANDARD",
                "action_type": "SEEK_LOW_DENSITY",
                "speed": 1.5,
                "accessibility_required": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            },
            headers=auth_headers,
        )

        body = resp.json()
        expected = sample_prediction.timestamp.isoformat()
        assert body["timestamp"] == expected
