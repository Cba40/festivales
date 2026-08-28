"""Tests para el endpoint públicas GET /api/emergencies.

Cubre:
- Contrato HTTP de la ruta (200, filtro por tipo, 422 por tipo inválido), con
  adapter mockeado.
- Lógica determinística del adapter (filtro por tipo, orden por distancia con
  GPS y manejo de emergencias sin coordenadas), con DB mockeada.
- Utilidad Haversine.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.emergency import Emergency, EmergencyType
from app.schemas.emergency import (
    EmergencyItem,
    EmergencyRecommendationResponse,
)
from src.interfaces.rest.emergency_product import (
    _haversine_distance_km,
    get_emergency_product_adapter,
)

CITY_ID = "00000000-0000-0000-0000-000000000001"
BASE_URL = "/api/emergencies"


def _make_emergency(
    *,
    name: str,
    emg_type: EmergencyType,
    latitude: float | None,
    longitude: float | None,
) -> Emergency:
    return Emergency(
        id=str(uuid4()),
        city_id=CITY_ID,
        name=name,
        type=emg_type,
        phone="+54 0 000 0000",
        emergency_number="911" if emg_type == EmergencyType.numero_emergencia else None,
        address="Dirección de prueba",
        reference="Referencia de prueba",
        latitude=latitude,
        longitude=longitude,
        services="Servicios de prueba",
        schedule="24 hs",
        active=True,
    )


# ─────────────────────────────────────────────────────────────
# Contrato HTTP de la ruta (adapter mockeado)
# ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def mock_response() -> EmergencyRecommendationResponse:
    return EmergencyRecommendationResponse(
        emergencies=[
            EmergencyItem(
                id=str(uuid4()),
                name="Bomberos Voluntarios",
                type=EmergencyType.bomberos,
                phone="+54 3525 421-100",
                emergency_number=None,
                address="Av. Independencia 200",
                reference="Junto a la plaza",
                latitude=-30.9815,
                longitude=-64.0935,
                services="Incendios y rescates",
                schedule="24 hs",
                active=True,
                distance_km=1.5,
            ),
            EmergencyItem(
                id=str(uuid4()),
                name="Emergencias 911",
                type=EmergencyType.numero_emergencia,
                phone=None,
                emergency_number="911",
                address=None,
                reference=None,
                latitude=None,
                longitude=None,
                services="Emergencias generales",
                schedule="24 hs",
                active=True,
                distance_km=None,
            ),
        ],
    )


@pytest.fixture(autouse=True)
def _mock_adapter(
    mock_response: EmergencyRecommendationResponse,
):
    with patch(
        "app.api.routes.emergency.get_emergency_product_adapter",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = mock_response
        yield mock


class TestEmergencyEndpoint:
    def test_emergency_endpoint_returns_200(
        self,
        client: TestClient,
        _mock_adapter: AsyncMock,
    ):
        resp = client.get(BASE_URL, params={"city_id": CITY_ID})

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["emergencies"]) == 2
        first = body["emergencies"][0]
        assert first["name"] == "Bomberos Voluntarios"
        assert first["type"] == "bomberos"
        assert first["distance_km"] == 1.5
        second = body["emergencies"][1]
        assert second["type"] == "numero_emergencia"
        assert second["distance_km"] is None

    def test_emergency_filters_by_type(
        self,
        client: TestClient,
        _mock_adapter: AsyncMock,
    ):
        resp = client.get(
            BASE_URL,
            params={"city_id": CITY_ID, "type": "salud"},
        )

        assert resp.status_code == 200
        _mock_adapter.assert_awaited_once()
        call_kwargs = _mock_adapter.await_args[1]
        assert call_kwargs["emergency_type"] == EmergencyType.salud
        assert call_kwargs["city_id"] == CITY_ID

    def test_emergency_invalid_type_returns_422(
        self,
        client: TestClient,
    ):
        resp = client.get(
            BASE_URL,
            params={"city_id": CITY_ID, "type": "meteorito"},
        )

        assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────
# Lógica determinística del adapter (DB mockeada)
# ─────────────────────────────────────────────────────────────

class TestEmergencyAdapter:
    @pytest.mark.asyncio
    async def test_adapter_filters_by_type(self):
        rows = [
            _make_emergency(name="Policía", emg_type=EmergencyType.policia, latitude=-30.98, longitude=-64.09),
            _make_emergency(name="Salud A", emg_type=EmergencyType.salud, latitude=-30.98, longitude=-64.09),
            _make_emergency(name="Bomberos C", emg_type=EmergencyType.bomberos, latitude=-30.98, longitude=-64.09),
        ]
        db = AsyncMock()
        result = MagicMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = rows
        result.scalars.return_value = scalars_result
        db.execute.return_value = result

        await get_emergency_product_adapter(
            db=db,
            city_id=CITY_ID,
            emergency_type=EmergencyType.salud,
        )

        stmt = db.execute.await_args[0][0]
        compiled = stmt.compile(compile_kwargs={"literal_binds": True})
        sql = str(compiled)
        assert "emergencies" in sql
        assert "type" in sql
        assert "'salud'" in sql

    @pytest.mark.asyncio
    async def test_adapter_sorts_by_distance_with_gps(self):
        rows = [
            _make_emergency(name="Lejos", emg_type=EmergencyType.policia, latitude=-31.0000, longitude=-64.1000),
            _make_emergency(name="Cerca", emg_type=EmergencyType.policia, latitude=-30.9810, longitude=-64.0900),
            # Número de emergencia sin coordenadas: va al final pese a ser el primero en nombre.
            _make_emergency(name="911 AA", emg_type=EmergencyType.numero_emergencia, latitude=None, longitude=None),
        ]
        db = AsyncMock()
        result = MagicMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = rows
        result.scalars.return_value = scalars_result
        db.execute.return_value = result

        result = await get_emergency_product_adapter(
            db=db,
            city_id=CITY_ID,
            user_latitude=-30.9800,
            user_longitude=-64.0900,
        )

        names = [e.name for e in result.emergencies]
        assert names == ["Cerca", "Lejos", "911 AA"]
        # Las que tienen distancia vienen primero, ordenadas ascendente;
        # las sin coordenadas quedan al final con distance_km = None.
        distances = [e.distance_km for e in result.emergencies]
        assert distances[:2] == sorted(d for d in distances[:2] if d is not None)
        assert result.emergencies[-1].distance_km is None

    @pytest.mark.asyncio
    async def test_adapter_sorts_by_name_without_gps(self):
        rows = [
            _make_emergency(name="Zeta Policía", emg_type=EmergencyType.policia, latitude=-30.98, longitude=-64.09),
            _make_emergency(name="Alfa Salud", emg_type=EmergencyType.salud, latitude=-30.98, longitude=-64.09),
            _make_emergency(name="911 Emergencias", emg_type=EmergencyType.numero_emergencia, latitude=None, longitude=None),
        ]
        db = AsyncMock()
        result = MagicMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = rows
        result.scalars.return_value = scalars_result
        db.execute.return_value = result

        result = await get_emergency_product_adapter(
            db=db,
            city_id=CITY_ID,
        )

        names = [e.name for e in result.emergencies]
        assert names == ["911 Emergencias", "Alfa Salud", "Zeta Policía"]
        # Sin GPS no debe calcular distancia
        assert all(e.distance_km is None for e in result.emergencies)

    @pytest.mark.asyncio
    async def test_adapter_applies_limit(self):
        rows = [
            _make_emergency(name=name, emg_type=EmergencyType.policia, latitude=-30.98, longitude=-64.09)
            for name in ["A", "B", "C"]
        ]
        db = AsyncMock()
        result = MagicMock()
        scalars_result = MagicMock()
        scalars_result.all.return_value = rows
        result.scalars.return_value = scalars_result
        db.execute.return_value = result

        result = await get_emergency_product_adapter(
            db=db,
            city_id=CITY_ID,
            limit=2,
        )

        assert len(result.emergencies) == 2


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
