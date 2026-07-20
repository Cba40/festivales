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
from app.schemas.product import HealthRecommendationResponse, ZonaSaludItem
from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState

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


ZONE_A = UUID("a0000000-0000-0000-0000-000000000001")
ZONE_B = UUID("a0000000-0000-0000-0000-000000000002")


@pytest.fixture
def sample_prediction() -> TerritorialPrediction:
    return TerritorialPrediction(
        timestamp=datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc),
        zone_states=[
            ZoneState(
                zone_id=ZONE_A,
                operational_state="LOW_DEMAND",
                availability=200,
                saturation_level=0.10,
                estimated_wait=0,
                confidence=0.95,
                reasoning_factors=["Baja densidad proyectada"],
                active_restriction=FlowRestriction.OPEN,
            ),
            ZoneState(
                zone_id=ZONE_B,
                operational_state="MODERATE_DEMAND",
                availability=80,
                saturation_level=0.55,
                estimated_wait=3,
                confidence=0.80,
                reasoning_factors=["Demanda moderada"],
                active_restriction=FlowRestriction.REGULATED,
            ),
        ],
        active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
        active_event_day_phase_id=UUID("30000000-0000-0000-0000-000000000001"),
    )


@pytest.fixture
def sample_recommendations() -> list[ZoneRecommendation]:
    return [
        ZoneRecommendation(
            zone_id=ZONE_A,
            score=0.90,
            reasoning=["Baja densidad proyectada"],
        ),
        ZoneRecommendation(
            zone_id=ZONE_B,
            score=0.65,
            reasoning=["Acceso regulado"],
        ),
    ]


@pytest.fixture(autouse=True)
def _mock_adapter(
    sample_prediction: TerritorialPrediction,
):
    with patch(
        "app.api.routes.health_product.get_health_product_adapter",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = HealthRecommendationResponse(
            event_id=EVENT_ID,
            timestamp=sample_prediction.timestamp.isoformat(),
            mode="informar",
            zonas=[
                ZonaSaludItem(
                    zone_id=str(ZONE_A),
                    name="Salud Norte",
                    score=0.90,
                    reasoning=["Baja densidad proyectada"],
                    saturation_level=0.10,
                    estado="bajo",
                    availability=200,
                    estimated_wait=0,
                    confidence=0.95,
                    active_restriction="OPEN",
                    operational_state="LOW_DEMAND",
                    lat=-30.95,
                    lng=-64.07,
                    referencia="Centro de salud",
                    distancia_min=3,
                ),
                ZonaSaludItem(
                    zone_id=str(ZONE_B),
                    name="Salud Sur",
                    score=0.65,
                    reasoning=["Acceso regulado"],
                    saturation_level=0.55,
                    estado="alto",
                    availability=80,
                    estimated_wait=3,
                    confidence=0.80,
                    active_restriction="REGULATED",
                    operational_state="MODERATE_DEMAND",
                    lat=-30.99,
                    lng=-64.10,
                    referencia="Cerca del escenario",
                    distancia_min=7,
                ),
            ],
        )
        yield mock


class TestHealthProductEndpoint:
    def test_200_ok(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"{BASE_URL}/products/health",
            params={
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
        assert body["mode"] == "informar"
        assert len(body["zonas"]) == 2

        first = body["zonas"][0]
        assert first["zone_id"] == str(ZONE_A)
        assert first["name"] == "Salud Norte"
        assert first["score"] == 0.90
        assert first["saturation_level"] == 0.10
        assert first["estado"] == "bajo"
        assert first["estimated_wait"] == 0
        assert first["confidence"] == 0.95
        assert first["active_restriction"] == "OPEN"
        assert first["lat"] == -30.95
        assert first["lng"] == -64.07
        assert first["referencia"] == "Centro de salud"
        assert first["distancia_min"] == 3

    def test_422_missing_required_params(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"{BASE_URL}/products/health",
            params={"speed": 1.5},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_401_no_auth(
        self,
        client: TestClient,
    ):
        resp = client.get(
            f"{BASE_URL}/products/health",
            params={
                "speed": 1.5,
                "accessibility_required": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            },
        )
        assert resp.status_code == 401

    def test_negative_speed(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"{BASE_URL}/products/health",
            params={
                "speed": -1.0,
                "accessibility_required": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_empty_zones(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
    ):
        _mock_adapter.return_value = HealthRecommendationResponse(
            event_id=EVENT_ID,
            timestamp=datetime.now(timezone.utc).isoformat(),
            mode="sin_solucion",
            zonas=[],
        )

        resp = client.get(
            f"{BASE_URL}/products/health",
            params={
                "speed": 1.5,
                "accessibility_required": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["mode"] == "sin_solucion"
        assert len(body["zonas"]) == 0

    def test_adapter_invoked_with_parsed_params(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
    ):
        client.get(
            f"{BASE_URL}/products/health",
            params={
                "speed": 1.5,
                "accessibility_required": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "current_zone_id": str(ZONE_A),
                "access_level": "VIP",
                "limit": 3,
            },
            headers=auth_headers,
        )

        _mock_adapter.assert_awaited_once()
        call_kwargs = _mock_adapter.await_args[1]

        assert call_kwargs["event_id"] == EVENT_ID
        assert call_kwargs["limit"] == 3

        user_ctx = call_kwargs["user_context"]
        assert user_ctx.access_level.value == "VIP"
        assert str(user_ctx.user_id) == "550e8400-e29b-41d4-a716-446655440000"

        mob_ctx = call_kwargs["mobility_context"]
        assert mob_ctx.speed == 1.5
        assert mob_ctx.accessibility_required is False
        assert str(mob_ctx.current_zone_id) == str(ZONE_A)

    def test_response_structure(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"{BASE_URL}/products/health",
            params={
                "speed": 1.5,
                "accessibility_required": False,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            },
            headers=auth_headers,
        )

        body = resp.json()
        zona = body["zonas"][0]

        expected_fields = {
            "zone_id", "name", "score", "reasoning",
            "saturation_level", "estado", "availability",
            "estimated_wait", "confidence", "active_restriction",
            "operational_state", "lat", "lng", "referencia", "distancia_min",
        }
        assert set(zona.keys()) == expected_fields
