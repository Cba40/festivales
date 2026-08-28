"""Tests for the GET /api/events/{event_id}/products/accommodation endpoint.

Cubre:
- Contrato HTTP de la ruta (200, 422 por tipo inválido), con adapter mockeado.
- Lógica determinística del adapter (filtro por tipo, orden por distancia,
  orden por nombre), con DB mockeada.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.db.session import get_async_db
from app.main import app
from app.models.accommodation import Accommodation, AccommodationType
from app.schemas.accommodation import (
    AccommodationItem,
    AccommodationRecommendationResponse,
)
from src.interfaces.rest.accommodation_product import (
    _haversine_distance_km,
    get_accommodation_product_adapter,
)

EVENT_ID = "test-event-1"
BASE_URL = f"/api/events/{EVENT_ID}"


def _make_accommodation(
    *,
    name: str,
    acc_type: AccommodationType,
    latitude: float | None,
    longitude: float | None,
) -> Accommodation:
    return Accommodation(
        id=str(uuid4()),
        event_id=EVENT_ID,
        name=name,
        type=acc_type,
        address="Dirección de prueba",
        reference="Referencia de prueba",
        latitude=latitude,
        longitude=longitude,
        phone="+54 0 000 0000",
        website="https://example.com",
        official_info_url="https://jesusmaria.gob.ar/turismo",
        active=True,
        created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        updated_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )


# ─────────────────────────────────────────────────────────────
# Contrato HTTP de la ruta (adapter mockeado)
# ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


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
def mock_response() -> AccommodationRecommendationResponse:
    return AccommodationRecommendationResponse(
        event_id=EVENT_ID,
        accommodations=[
            AccommodationItem(
                id=str(uuid4()),
                event_id=EVENT_ID,
                name="Hotel de la Estación",
                type=AccommodationType.HOTEL,
                address="Av. Independencia 1250",
                reference="Cerca del anfiteatro",
                latitude=-30.9815,
                longitude=-64.0935,
                phone="+54 3525 420-101",
                website="https://hoteldelaestacion.com.ar",
                official_info_url="https://jesusmaria.gob.ar/turismo",
                active=True,
                distance_km=1.2,
                created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            ),
        ],
    )


@pytest.fixture(autouse=True)
def _mock_adapter(
    mock_response: AccommodationRecommendationResponse,
):
    with patch(
        "app.api.routes.accommodation.get_accommodation_product_adapter",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = mock_response
        yield mock


class TestAccommodationProductEndpoint:
    def test_accommodation_endpoint_returns_200(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
    ):
        resp = client.get(
            f"{BASE_URL}/products/accommodation",
            headers=auth_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["event_id"] == EVENT_ID
        assert len(body["accommodations"]) == 1
        acc = body["accommodations"][0]
        assert acc["name"] == "Hotel de la Estación"
        assert acc["type"] == "hotel"
        assert acc["distance_km"] == 1.2

    def test_accommodation_filters_by_type(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
    ):
        resp = client.get(
            f"{BASE_URL}/products/accommodation",
            params={"type": "hotel"},
            headers=auth_headers,
        )

        assert resp.status_code == 200
        _mock_adapter.assert_awaited_once()
        call_kwargs = _mock_adapter.await_args[1]
        assert call_kwargs["acc_type"] == AccommodationType.HOTEL
        assert call_kwargs["event_id"] == EVENT_ID

    def test_accommodation_invalid_type_returns_422(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"{BASE_URL}/products/accommodation",
            params={"type": "motel"},
            headers=auth_headers,
        )

        assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────
# Lógica determinística del adapter (DB mockeada)
# ─────────────────────────────────────────────────────────────

class TestAccommodationAdapter:
    @pytest.mark.asyncio
    async def test_adapter_filters_by_type(self):
        rows = [
            _make_accommodation(name="Hotel A", acc_type=AccommodationType.HOTEL, latitude=-30.98, longitude=-64.09),
            _make_accommodation(name="Hostel B", acc_type=AccommodationType.HOSTEL, latitude=-30.98, longitude=-64.09),
            _make_accommodation(name="Camping C", acc_type=AccommodationType.CAMPING, latitude=-30.98, longitude=-64.09),
        ]
        db = AsyncMock()
        result = MagicMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = rows
        result.scalars.return_value = scalars_result
        db.execute.return_value = result

        await get_accommodation_product_adapter(
            db=db,
            event_id=EVENT_ID,
            acc_type=AccommodationType.HOTEL,
        )

        # El filtro por tipo se aplica a nivel de query (WHERE ... type = 'hotel').
        # Verificamos que el statement compilado incluya la condición del tipo.
        stmt = db.execute.await_args[0][0]
        compiled = stmt.compile(compile_kwargs={"literal_binds": True})
        sql = str(compiled)
        assert "accommodations" in sql
        assert "type" in sql
        assert "'hotel'" in sql

    @pytest.mark.asyncio
    async def test_adapter_sorts_by_distance_with_gps(self):
        rows = [
            _make_accommodation(name="Lejos", acc_type=AccommodationType.HOTEL, latitude=-31.0000, longitude=-64.1000),
            _make_accommodation(name="Cerca", acc_type=AccommodationType.HOTEL, latitude=-30.9810, longitude=-64.0900),
            _make_accommodation(name="Medio", acc_type=AccommodationType.HOTEL, latitude=-30.9900, longitude=-64.0950),
        ]
        db = AsyncMock()
        result = MagicMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = rows
        result.scalars.return_value = scalars_result
        db.execute.return_value = result

        result = await get_accommodation_product_adapter(
            db=db,
            event_id=EVENT_ID,
            user_latitude=-30.9800,
            user_longitude=-64.0900,
        )

        names = [a.name for a in result.accommodations]
        assert names == ["Cerca", "Medio", "Lejos"]
        distances = [a.distance_km for a in result.accommodations]
        assert distances == sorted(d for d in distances if d is not None)

    @pytest.mark.asyncio
    async def test_adapter_sorts_by_name_without_gps(self):
        rows = [
            _make_accommodation(name="Zeta Hotel", acc_type=AccommodationType.HOTEL, latitude=-30.98, longitude=-64.09),
            _make_accommodation(name="Alfa Hostel", acc_type=AccommodationType.HOSTEL, latitude=-30.98, longitude=-64.09),
            _make_accommodation(name="Bravo Camping", acc_type=AccommodationType.CAMPING, latitude=-30.98, longitude=-64.09),
        ]
        db = AsyncMock()
        result = MagicMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = rows
        result.scalars.return_value = scalars_result
        db.execute.return_value = result

        result = await get_accommodation_product_adapter(
            db=db,
            event_id=EVENT_ID,
        )

        names = [a.name for a in result.accommodations]
        assert names == ["Alfa Hostel", "Bravo Camping", "Zeta Hotel"]
        # Sin GPS no debe calcular distancia
        assert all(a.distance_km is None for a in result.accommodations)


# ─────────────────────────────────────────────────────────────
# Utilidad Haversine
# ─────────────────────────────────────────────────────────────

class TestHaversine:
    def test_haversine_known_distance(self):
        # Buenos Aires (-34.6037, -58.3816) → Córdoba (-31.4201, -64.1888)
        # distancia real ≈ 695 km
        d = _haversine_distance_km(-34.6037, -58.3816, -31.4201, -64.1888)
        assert 600 < d < 800

    def test_haversine_zero_distance(self):
        d = _haversine_distance_km(-30.98, -64.09, -30.98, -64.09)
        assert d == pytest.approx(0.0, abs=1e-6)
