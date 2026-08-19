"""Tests para la API CRUD de `service_configs`.

Todo acceso a DB es mockeado; se valida solo el contrato HTTP de las rutas
(list, create, update, delete), la unicidad default/override (409), las
validaciones (422), los 404 y la deterministidad del orden.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.db.session import get_async_db
from app.main import app


@pytest.fixture(autouse=True)
def _clean_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def mock_async_db():
    db = AsyncMock()
    db.add = MagicMock()
    return db


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


BASE_URL = "/api/service-configs"
NOW = "2026-08-18T12:00:00Z"

DEFAULT_CONFIG = {
    "id": "c0000000-0000-0000-0000-000000000001",
    "zone_type_id": "a0000000-0000-0000-0000-000000000001",
    "subtipo": None,
    "event_day_id": None,
    "average_duration_min": 15,
    "created_at": NOW,
    "updated_at": NOW,
}

OVERRIDE_CONFIG = {
    **DEFAULT_CONFIG,
    "id": "c0000000-0000-0000-0000-000000000002",
    "event_day_id": "b0000000-0000-0000-0000-000000000001",
    "average_duration_min": 25,
}


def _as_model_attrs(data: dict) -> object:
    class FakeModel:
        pass

    obj = FakeModel()
    for k, v in data.items():
        setattr(obj, k, v)
    return obj


def _mock_scalar_result(mock_db: AsyncMock, return_value: object) -> None:
    result = MagicMock()
    result.scalar_one_or_none.return_value = return_value
    mock_db.execute.return_value = result


def _mock_scalars_result(mock_db: AsyncMock, rows: list[object]) -> None:
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    mock_db.execute.return_value = result


def _enable_refresh_timestamps(mock_db: AsyncMock) -> None:
    async def _refresh(config) -> None:
        config.created_at = NOW
        config.updated_at = NOW

    mock_db.refresh.side_effect = _refresh


def _compiled_sql(mock_db: AsyncMock) -> str:
    from sqlalchemy.dialects import postgresql

    stmt = mock_db.execute.call_args[0][0]
    return str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


class TestListServiceConfigs:
    def test_returns_defaults_when_no_event_day(self, client, auth_headers, mock_async_db):
        _mock_scalars_result(mock_async_db, [_as_model_attrs(DEFAULT_CONFIG)])
        response = client.get(BASE_URL, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == DEFAULT_CONFIG["id"]
        assert data[0]["event_day_id"] is None
        assert data[0]["average_duration_min"] == 15
        sql = _compiled_sql(mock_async_db)
        assert "event_day_id IS NULL" in sql
        assert "ORDER BY" in sql

    def test_returns_overrides_when_event_day(self, client, auth_headers, mock_async_db):
        _mock_scalars_result(mock_async_db, [_as_model_attrs(OVERRIDE_CONFIG)])
        response = client.get(
            BASE_URL,
            params={"event_day_id": OVERRIDE_CONFIG["event_day_id"]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["event_day_id"] == OVERRIDE_CONFIG["event_day_id"]
        sql = _compiled_sql(mock_async_db)
        assert f"event_day_id = '{OVERRIDE_CONFIG['event_day_id']}'" in sql
        assert "IS NULL" not in sql

    def test_filters_by_zone_type_and_subtipo(self, client, auth_headers, mock_async_db):
        _mock_scalars_result(mock_async_db, [])
        response = client.get(
            BASE_URL,
            params={"zone_type_id": DEFAULT_CONFIG["zone_type_id"], "subtipo": "banos"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        sql = _compiled_sql(mock_async_db)
        assert f"zone_type_id = '{DEFAULT_CONFIG['zone_type_id']}'" in sql
        assert "coalesce(service_configs.subtipo, '') = 'banos'" in sql

    def test_returns_empty_list(self, client, auth_headers, mock_async_db):
        _mock_scalars_result(mock_async_db, [])
        response = client.get(BASE_URL, headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_deterministic_order(self, client, auth_headers, mock_async_db):
        _mock_scalars_result(mock_async_db, [])
        response = client.get(BASE_URL, headers=auth_headers)
        assert response.status_code == 200
        sql = _compiled_sql(mock_async_db)
        assert "ORDER BY service_configs.zone_type_id, service_configs.subtipo" in sql

    def test_returns_401_without_auth(self, client):
        response = client.get(BASE_URL)
        assert response.status_code == 401


class TestCreateServiceConfig:
    def test_creates_default_config(self, client, auth_headers, mock_async_db):
        _mock_scalar_result(mock_async_db, None)
        _enable_refresh_timestamps(mock_async_db)
        payload = {"zone_type_id": DEFAULT_CONFIG["zone_type_id"], "average_duration_min": 15}
        response = client.post(BASE_URL, json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["zone_type_id"] == DEFAULT_CONFIG["zone_type_id"]
        assert data["subtipo"] is None
        assert data["event_day_id"] is None
        assert data["average_duration_min"] == 15
        assert UUID(data["id"])
        created = mock_async_db.add.call_args[0][0]
        assert created.id == data["id"]

    def test_creates_override_config(self, client, auth_headers, mock_async_db):
        _mock_scalar_result(mock_async_db, None)
        _enable_refresh_timestamps(mock_async_db)
        payload = {
            "zone_type_id": DEFAULT_CONFIG["zone_type_id"],
            "subtipo": "banos",
            "event_day_id": OVERRIDE_CONFIG["event_day_id"],
            "average_duration_min": 25,
        }
        response = client.post(BASE_URL, json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["event_day_id"] == OVERRIDE_CONFIG["event_day_id"]
        assert data["average_duration_min"] == 25

    def test_409_when_default_exists(self, client, auth_headers, mock_async_db):
        _mock_scalar_result(mock_async_db, _as_model_attrs(DEFAULT_CONFIG))
        payload = {"zone_type_id": DEFAULT_CONFIG["zone_type_id"], "average_duration_min": 15}
        response = client.post(BASE_URL, json=payload, headers=auth_headers)
        assert response.status_code == 409

    def test_409_when_override_exists(self, client, auth_headers, mock_async_db):
        _mock_scalar_result(mock_async_db, _as_model_attrs(OVERRIDE_CONFIG))
        payload = {
            "zone_type_id": DEFAULT_CONFIG["zone_type_id"],
            "event_day_id": OVERRIDE_CONFIG["event_day_id"],
            "average_duration_min": 25,
        }
        response = client.post(BASE_URL, json=payload, headers=auth_headers)
        assert response.status_code == 409

    def test_409_empty_subtipo_matches_null_default(self, client, auth_headers, mock_async_db):
        _mock_scalar_result(mock_async_db, _as_model_attrs(DEFAULT_CONFIG))
        payload = {
            "zone_type_id": DEFAULT_CONFIG["zone_type_id"],
            "subtipo": "",
            "average_duration_min": 15,
        }
        response = client.post(BASE_URL, json=payload, headers=auth_headers)
        assert response.status_code == 409

    def test_422_zero_duration(self, client, auth_headers):
        payload = {"zone_type_id": DEFAULT_CONFIG["zone_type_id"], "average_duration_min": 0}
        response = client.post(BASE_URL, json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_422_negative_duration(self, client, auth_headers):
        payload = {"zone_type_id": DEFAULT_CONFIG["zone_type_id"], "average_duration_min": -5}
        response = client.post(BASE_URL, json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_401_without_auth(self, client):
        payload = {"zone_type_id": DEFAULT_CONFIG["zone_type_id"], "average_duration_min": 15}
        response = client.post(BASE_URL, json=payload)
        assert response.status_code == 401


class TestUpdateServiceConfig:
    URL = f"{BASE_URL}/{DEFAULT_CONFIG['id']}"

    def test_updates_duration(self, client, auth_headers, mock_async_db):
        _mock_scalar_result(mock_async_db, _as_model_attrs(DEFAULT_CONFIG))
        _enable_refresh_timestamps(mock_async_db)
        response = client.put(self.URL, json={"average_duration_min": 30}, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["average_duration_min"] == 30

    def test_404_when_not_found(self, client, auth_headers, mock_async_db):
        _mock_scalar_result(mock_async_db, None)
        response = client.put(self.URL, json={"average_duration_min": 30}, headers=auth_headers)
        assert response.status_code == 404

    def test_422_zero_duration(self, client, auth_headers, mock_async_db):
        _mock_scalar_result(mock_async_db, _as_model_attrs(DEFAULT_CONFIG))
        response = client.put(self.URL, json={"average_duration_min": 0}, headers=auth_headers)
        assert response.status_code == 422

    def test_422_negative_duration(self, client, auth_headers, mock_async_db):
        _mock_scalar_result(mock_async_db, _as_model_attrs(DEFAULT_CONFIG))
        response = client.put(self.URL, json={"average_duration_min": -5}, headers=auth_headers)
        assert response.status_code == 422

    def test_401_without_auth(self, client):
        response = client.put(self.URL, json={"average_duration_min": 30})
        assert response.status_code == 401


class TestDeleteServiceConfig:
    URL = f"{BASE_URL}/{DEFAULT_CONFIG['id']}"

    def test_deletes(self, client, auth_headers, mock_async_db):
        _mock_scalar_result(mock_async_db, _as_model_attrs(DEFAULT_CONFIG))
        response = client.delete(self.URL, headers=auth_headers)
        assert response.status_code == 204
        assert response.content == b""
        mock_async_db.delete.assert_awaited_once()

    def test_404_when_not_found(self, client, auth_headers, mock_async_db):
        _mock_scalar_result(mock_async_db, None)
        response = client.delete(self.URL, headers=auth_headers)
        assert response.status_code == 404

    def test_401_without_auth(self, client):
        response = client.delete(self.URL)
        assert response.status_code == 401