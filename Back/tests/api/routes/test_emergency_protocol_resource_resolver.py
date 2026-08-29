"""Tests del endpoint público de resolución de recursos (Emergencia V2 - S3).

Endpoint: ``GET /api/emergency-protocols/recommended-resource``.

Cubre:
- Resolución con GPS (Haversine) y sin GPS (alfabética).
- Determinismo (desempate por id ASC) y filtros city_id/active.
- 404 sin recurso compatible, 422 por parámetros inválidos/ausentes.
- Acceso público sin token.

Patrón idéntico a V1/S2: ``AsyncMock`` de ``get_async_db`` +
``app.dependency_overrides``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_async_db
from app.models.emergency import Emergency, EmergencyType

BASE_URL = "/api/emergency-protocols/recommended-resource"

CITY_A = str(uuid4())
CITY_B = str(uuid4())


def _make_resource(
    name: str,
    city_id: str,
    *,
    resource_id: str | None = None,
    type_: EmergencyType = EmergencyType.policia,
    latitude: float | None = None,
    longitude: float | None = None,
    active: bool = True,
) -> Emergency:
    now = datetime.now(timezone.utc)
    return Emergency(
        id=resource_id or str(uuid4()),
        city_id=city_id,
        name=name,
        type=type_,
        phone=None,
        emergency_number=None,
        address=None,
        reference=None,
        latitude=latitude,
        longitude=longitude,
        services=None,
        schedule=None,
        active=active,
        created_at=now,
        updated_at=now,
    )


def _override_db(rows: list[Emergency]) -> AsyncMock:
    db = AsyncMock()
    result = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = rows
    result.scalars.return_value = scalars_result
    db.execute.return_value = result

    async def _fake_get_db():
        yield db

    app.dependency_overrides[get_async_db] = _fake_get_db
    return db


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _get(client: TestClient, **params) -> object:
    clean = {k: v for k, v in params.items() if v is not None}
    return client.get(BASE_URL, params=clean)


class TestRecommendedResourceEndpoint:
    def test_resolve_with_location_returns_closest(self, client: TestClient):
        _override_db([
            _make_resource(
                "Bomberos lejos", CITY_A, type_=EmergencyType.bomberos,
                latitude=-31.0, longitude=-64.0,
            ),
            _make_resource(
                "Bomberos cerca", CITY_A, type_=EmergencyType.bomberos,
                latitude=-31.0, longitude=-64.3,
            ),
        ])
        resp = _get(
            client,
            target_type="bomberos",
            city_id=CITY_A,
            latitude=-31.0,
            longitude=-64.3,
        )

        assert resp.status_code == 200
        assert resp.json()["name"] == "Bomberos cerca"

    def test_resolve_without_location_returns_alphabetical(self, client: TestClient):
        _override_db([
            _make_resource("Zeta Central", CITY_A),
            _make_resource("Alfa Central", CITY_A),
        ])
        resp = _get(client, target_type="policia", city_id=CITY_A)

        assert resp.status_code == 200
        assert resp.json()["name"] == "Alfa Central"

    def test_resolve_no_resource_of_type_returns_404(self, client: TestClient):
        _override_db([
            _make_resource("Cuartel", CITY_A, type_=EmergencyType.bomberos),
        ])
        resp = _get(client, target_type="salud", city_id=CITY_A)

        assert resp.status_code == 404
        assert resp.json()["detail"] == "No hay recurso compatible disponible"

    def test_resolve_invalid_target_type_422(self, client: TestClient):
        _override_db([])
        resp = _get(client, target_type="invalido", city_id=CITY_A)

        assert resp.status_code == 422

    def test_resolve_missing_city_id_422(self, client: TestClient):
        _override_db([])
        resp = _get(client, target_type="policia")

        assert resp.status_code == 422

    def test_resolve_deterministic_same_input_same_output(self, client: TestClient):
        id_a = "00000000-0000-0000-0000-000000000001"
        id_b = "00000000-0000-0000-0000-000000000002"
        _override_db([
            _make_resource(
                "Misma distancia 1", CITY_A, resource_id=id_a,
                latitude=-31.42, longitude=-64.18,
            ),
            _make_resource(
                "Misma distancia 2", CITY_A, resource_id=id_b,
                latitude=-31.42, longitude=-64.18,
            ),
        ])
        params = dict(
            target_type="policia",
            city_id=CITY_A,
            latitude=-31.42,
            longitude=-64.18,
        )

        first = _get(client, **params)
        second = _get(client, **params)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["id"] == second.json()["id"]
        assert first.json()["id"] == id_a  # desempate por id ASC

    def test_resolve_filters_by_city_id(self, client: TestClient):
        _override_db([
            _make_resource("Cuartel otra ciudad", CITY_B),
        ])
        resp = _get(client, target_type="policia", city_id=CITY_A)

        assert resp.status_code == 404

    def test_resolve_filters_active_only(self, client: TestClient):
        _override_db([
            _make_resource("Cuartel inactivo", CITY_A, active=False),
        ])
        resp = _get(client, target_type="policia", city_id=CITY_A)

        assert resp.status_code == 404

    def test_resolve_public_without_token(self, client: TestClient):
        _override_db([
            _make_resource("Cuartel Central", CITY_A),
        ])
        resp = _get(client, target_type="policia", city_id=CITY_A)
        assert resp.status_code == 200

        # copia directa por si _get filtra: sin Authorization en el primer 200
        assert "Authorization" not in str(resp.request.headers) or "Bearer" not in str(
            resp.request.headers
        )

    def test_resolve_ignores_inactive_resources(self, client: TestClient):
        _override_db([
            _make_resource(
                "Cuartel viejo", CITY_A, latitude=-31.0, longitude=-64.0,
                active=False,
            ),
            _make_resource(
                "Cuartel vigente", CITY_A, latitude=-31.4, longitude=-64.2,
            ),
        ])
        resp = _get(client, target_type="policia", city_id=CITY_A)

        assert resp.status_code == 200
        assert resp.json()["name"] == "Cuartel vigente"