from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, AsyncMock, patch

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


NOW = "2026-07-22T12:00:00Z"

DEFAULT_RECOMMENDATION_CONFIG = {
    "low_density_saturation_threshold": 0.5,
    "low_density_reasoning_threshold": 0.3,
    "regulated_penalty": 0.3,
    "vip_bonus": 0.1,
    "staff_bonus": 0.2,
    "mobility_penalty": 0.15,
    "created_at": NOW,
    "updated_at": NOW,
}

DEFAULT_STAGE4_CONFIG = {
    "saturation_high_threshold": 0.9,
    "saturation_moderate_threshold": 0.5,
    "confidence_no_events": 1.0,
    "confidence_planned_events": 0.8,
    "confidence_incident": 0.5,
    "wait_time_mapping": [
        [0.0, 0.3, 0],
        [0.3, 0.5, 5],
        [0.5, 0.7, 10],
        [0.7, 0.9, 15],
        [0.9, 1.01, 20],
    ],
    "created_at": NOW,
    "updated_at": NOW,
}

UPDATED_RECOMMENDATION_CONFIG = {
    **DEFAULT_RECOMMENDATION_CONFIG,
    "low_density_saturation_threshold": 0.8,
}

UPDATED_STAGE4_CONFIG = {
    **DEFAULT_STAGE4_CONFIG,
    "saturation_high_threshold": 0.95,
}

RECOMMENDATION_ROUTES = "app.api.routes.motor_config"
STAGE4_ROUTES = "app.api.routes.motor_config"


def _as_model_attrs(data: dict) -> object:
    class FakeModel:
        pass

    obj = FakeModel()
    for k, v in data.items():
        setattr(obj, k, v)
    return obj


def _mock_db_query(mock_db: AsyncMock, return_value: object) -> None:
    from unittest.mock import MagicMock

    result = MagicMock()
    result.scalar_one_or_none.return_value = return_value
    mock_db.execute.return_value = result


class TestGetRecommendationConfig:
    GET_URL = "/api/recommendation-config"

    def test_returns_default_config(self, client, auth_headers):
        with patch(f"{RECOMMENDATION_ROUTES}.crud_get_recommendation_config", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _as_model_attrs(DEFAULT_RECOMMENDATION_CONFIG)
            response = client.get(self.GET_URL, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["low_density_saturation_threshold"] == 0.5
        assert data["low_density_reasoning_threshold"] == 0.3

    def test_returns_401_without_auth(self, client):
        response = client.get(self.GET_URL)
        assert response.status_code == 401


class TestPutRecommendationConfig:
    PUT_URL = "/api/recommendation-config"

    def test_updates_and_returns_config(self, client, auth_headers):
        with patch(f"{RECOMMENDATION_ROUTES}.crud_update_recommendation_config", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = _as_model_attrs(UPDATED_RECOMMENDATION_CONFIG)
            payload = {"low_density_saturation_threshold": 0.8}
            response = client.put(self.PUT_URL, json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["low_density_saturation_threshold"] == 0.8

    def test_rejects_invalid_threshold_gt_1(self, client, auth_headers):
        payload = {"low_density_saturation_threshold": 1.5}
        response = client.put(self.PUT_URL, json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_rejects_invalid_threshold_lt_0(self, client, auth_headers):
        payload = {"low_density_saturation_threshold": -0.1}
        response = client.put(self.PUT_URL, json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_calls_configure_recommendation(self, client, auth_headers, mock_async_db):
        model = _as_model_attrs(DEFAULT_RECOMMENDATION_CONFIG)
        _mock_db_query(mock_async_db, model)
        with patch("app.crud.motor_config.configure_recommendation") as mock_configure:
            payload = {"low_density_saturation_threshold": 0.9}
            response = client.put(self.PUT_URL, json=payload, headers=auth_headers)
        assert response.status_code == 200
        mock_configure.assert_called_once()
        called_config = mock_configure.call_args[0][0]
        assert called_config.low_density_saturation_threshold == 0.9

    def test_returns_401_without_auth(self, client):
        payload = {"low_density_saturation_threshold": 0.8}
        response = client.put(self.PUT_URL, json=payload)
        assert response.status_code == 401


class TestGetStage4Config:
    GET_URL = "/api/stage4-config"

    def test_returns_default_config(self, client, auth_headers):
        with patch(f"{STAGE4_ROUTES}.crud_get_stage4_config", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = _as_model_attrs(DEFAULT_STAGE4_CONFIG)
            response = client.get(self.GET_URL, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["saturation_high_threshold"] == 0.9
        assert data["saturation_moderate_threshold"] == 0.5
        assert len(data["wait_time_mapping"]) == 5
        assert data["wait_time_mapping"][0] == [0.0, 0.3, 0]

    def test_returns_401_without_auth(self, client):
        response = client.get(self.GET_URL)
        assert response.status_code == 401


class TestPutStage4Config:
    PUT_URL = "/api/stage4-config"

    def test_updates_and_returns_config(self, client, auth_headers):
        with patch(f"{STAGE4_ROUTES}.crud_update_stage4_config", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = _as_model_attrs(UPDATED_STAGE4_CONFIG)
            payload = {"saturation_high_threshold": 0.95}
            response = client.put(self.PUT_URL, json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["saturation_high_threshold"] == 0.95

    def test_updates_wait_time_mapping(self, client, auth_headers):
        updated = {**DEFAULT_STAGE4_CONFIG, "wait_time_mapping": [[0.0, 0.2, 0], [0.2, 0.5, 5], [0.5, 1.0, 10]]}
        with patch(f"{STAGE4_ROUTES}.crud_update_stage4_config", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = _as_model_attrs(updated)
            payload = {"wait_time_mapping": [[0.0, 0.2, 0], [0.2, 0.5, 5], [0.5, 1.0, 10]]}
            response = client.put(self.PUT_URL, json=payload, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["wait_time_mapping"]) == 3

    def test_rejects_threshold_gt_1(self, client, auth_headers):
        payload = {"saturation_high_threshold": 1.5}
        response = client.put(self.PUT_URL, json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_rejects_invalid_wait_time_mapping_row_length(self, client, auth_headers):
        payload = {"wait_time_mapping": [[0.0, 0.5]]}
        response = client.put(self.PUT_URL, json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_rejects_wait_time_mapping_non_numeric(self, client, auth_headers):
        payload = {"wait_time_mapping": [["a", 0.5, 0]]}
        response = client.put(self.PUT_URL, json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_rejects_wait_time_mapping_high_lt_low(self, client, auth_headers):
        payload = {"wait_time_mapping": [[0.5, 0.3, 5]]}
        response = client.put(self.PUT_URL, json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_rejects_wait_time_mapping_empty(self, client, auth_headers):
        payload = {"wait_time_mapping": []}
        response = client.put(self.PUT_URL, json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_rejects_wait_time_mapping_negative_minutes(self, client, auth_headers):
        payload = {"wait_time_mapping": [[0.0, 0.5, -1]]}
        response = client.put(self.PUT_URL, json=payload, headers=auth_headers)
        assert response.status_code == 422

    def test_calls_configure_stage4(self, client, auth_headers, mock_async_db):
        model = _as_model_attrs(DEFAULT_STAGE4_CONFIG)
        _mock_db_query(mock_async_db, model)
        with patch("app.crud.motor_config.configure_stage4") as mock_configure:
            payload = {"saturation_high_threshold": 0.85}
            response = client.put(self.PUT_URL, json=payload, headers=auth_headers)
        assert response.status_code == 200
        mock_configure.assert_called_once()
        called_config = mock_configure.call_args[0][0]
        assert called_config.saturation_high_threshold == 0.85

    def test_returns_401_without_auth(self, client):
        payload = {"saturation_high_threshold": 0.95}
        response = client.put(self.PUT_URL, json=payload)
        assert response.status_code == 401
