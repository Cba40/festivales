"""Tests for the GET /api/events/{event_id}/predictions endpoint.

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
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.domain.entities.zone_behavior import FlowRestriction

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
        zone_states=[
            ZoneState(
                zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
                operational_state="NORMAL",
                availability=500,
                saturation_level=0.35,
                estimated_wait=5,
                confidence=0.9,
                reasoning_factors=["Demanda histórica baja"],
                active_restriction=FlowRestriction.OPEN,
            ),
            ZoneState(
                zone_id=UUID("a0000000-0000-0000-0000-000000000002"),
                operational_state="HIGH_DEMAND",
                availability=120,
                saturation_level=0.82,
                estimated_wait=25,
                confidence=0.75,
                reasoning_factors=["Alta concentración", "Evento activo"],
                active_restriction=FlowRestriction.REGULATED,
            ),
        ],
        active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
        active_event_day_phase_id=UUID("30000000-0000-0000-0000-000000000001"),
    )


@pytest.fixture(autouse=True)
def _mock_adapter(sample_prediction: TerritorialPrediction):
    with patch(
        "app.api.routes.predictions.get_territorial_prediction_adapter",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = sample_prediction
        yield mock


class TestPredictionsEndpoint:
    def test_200_ok(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"{BASE_URL}/predictions",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["timestamp"] == "2026-07-10T20:00:00+00:00"
        assert body["active_phase_id"] == "10000000-0000-0000-0000-000000000001"
        assert body["active_event_day_phase_id"] == "30000000-0000-0000-0000-000000000001"
        assert len(body["zone_states"]) == 2

    def test_200_zone_state_fields(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"{BASE_URL}/predictions",
            headers=auth_headers,
        )

        body = resp.json()
        zs = body["zone_states"][0]
        assert zs["zone_id"] == "a0000000-0000-0000-0000-000000000001"
        assert zs["operational_state"] == "NORMAL"
        assert zs["availability"] == 500
        assert zs["saturation_level"] == 0.35
        assert zs["estimated_wait"] == 5
        assert zs["confidence"] == 0.9
        assert zs["reasoning_factors"] == ["Demanda histórica baja"]
        assert zs["active_restriction"] == "OPEN"

    def test_200_second_zone_restriction(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"{BASE_URL}/predictions",
            headers=auth_headers,
        )

        body = resp.json()
        zs = body["zone_states"][1]
        assert zs["zone_id"] == "a0000000-0000-0000-0000-000000000002"
        assert zs["active_restriction"] == "REGULATED"
        assert zs["estimated_wait"] == 25
        assert zs["reasoning_factors"] == ["Alta concentración", "Evento activo"]

    def test_404_no_prediction(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
    ):
        _mock_adapter.return_value = None

        resp = client.get(
            f"{BASE_URL}/predictions",
            headers=auth_headers,
        )

        assert resp.status_code == 404

    def test_500_adapter_error(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
    ):
        _mock_adapter.side_effect = RuntimeError("engine failure")

        resp = client.get(
            f"{BASE_URL}/predictions",
            headers=auth_headers,
        )

        assert resp.status_code == 500

    def test_401_no_auth(
        self,
        client: TestClient,
    ):
        resp = client.get(
            f"{BASE_URL}/predictions",
        )

        assert resp.status_code == 401

    def test_adapter_invoked_once(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
    ):
        client.get(
            f"{BASE_URL}/predictions",
            headers=auth_headers,
        )

        _mock_adapter.assert_awaited_once()
        call_kwargs = _mock_adapter.await_args[1]
        assert call_kwargs["event_id"] == EVENT_ID
        assert "timestamp" in call_kwargs

    def test_response_timestamp_from_prediction(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
        sample_prediction: TerritorialPrediction,
    ):
        resp = client.get(
            f"{BASE_URL}/predictions",
            headers=auth_headers,
        )

        body = resp.json()
        expected = sample_prediction.timestamp.isoformat()
        assert body["timestamp"] == expected
