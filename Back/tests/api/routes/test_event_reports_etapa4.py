"""Tests de los endpoints get de informes municipales (ETAPA 4).

Cubre ``/temporal_distribution`` y ``/recommended_zones``. El acceso a BD se
simula por completo (misma técnica que ``test_analytics_evaluate.py``): se
valida el contrato HTTP, la autenticación JWT existente, la conversión a hora
local antes de agrupar y la resolución de fases en memoria sin N+1.
"""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.db.session import get_async_db
from app.main import app

ENDPOINT_TEMPLATE = "/api/events/{event_id}/reports"
EVENT_ID = "test-event-1"
EVENT_START = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
EVENT_END = datetime(2026, 9, 22, 23, 59, tzinfo=timezone.utc)
ARGENTINA = "America/Argentina/Buenos_Aires"

ETAPA4_ENDPOINTS = ["temporal_distribution", "recommended_zones"]


def _event(start_date=None, end_date=None):
    return SimpleNamespace(
        id=EVENT_ID,
        name="Festival de la Primavera 2026",
        start_date=start_date,
        end_date=end_date,
    )


def _event_result(event=None):
    res = MagicMock()
    res.scalar_one_or_none.return_value = event
    return res


def _all_result(rows):
    res = MagicMock()
    res.all.return_value = rows
    return res


def _scalars_result(rows):
    res = MagicMock()
    res.scalars.return_value.all.return_value = rows
    return res


def _one_result(value):
    res = MagicMock()
    res.one.return_value = value
    return res


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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
def db_mock() -> AsyncMock:
    db = AsyncMock()

    async def override():
        yield db

    app.dependency_overrides[get_async_db] = override
    return db


class TestEtapa4Auth:
    @pytest.mark.parametrize("report", ETAPA4_ENDPOINTS)
    def test_401_without_token(self, client: TestClient, db_mock: AsyncMock, report: str):
        resp = client.get(f"/api/events/{EVENT_ID}/reports/{report}")
        assert resp.status_code == 401

    @pytest.mark.parametrize("report", ETAPA4_ENDPOINTS)
    def test_404_event_not_found(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
        report: str,
    ):
        db_mock.execute.return_value = _event_result(None)
        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/{report}",
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Event not found"


class TestTemporalDistribution:
    def test_hour_buckets_local_timezone_with_phase(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        bucket_1 = datetime(2026, 9, 21, 15, 0)
        bucket_2 = datetime(2026, 9, 21, 16, 0)
        phase_id = "00000000-0000-0000-0000-000000000001"
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result(
                [
                    SimpleNamespace(bucket=bucket_1, count=5),
                    SimpleNamespace(bucket=bucket_2, count=3),
                ]
            ),
            _scalars_result([SimpleNamespace(id="ed1", date=date(2026, 9, 21))]),
            _scalars_result(
                [
                    SimpleNamespace(
                        event_day_id="ed1",
                        operational_phase_id=phase_id,
                        start_min=900,
                        end_min=1260,
                    )
                ]
            ),
            _scalars_result([SimpleNamespace(id=phase_id, name="tarde")]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/temporal_distribution",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["event_id"] == EVENT_ID
        assert body["granularity"] == "hour"
        assert body["timezone"] == ARGENTINA
        assert body["service_category"] is None
        assert _parse_iso(body["period"]["start"]) == EVENT_START
        assert body["buckets"][0] == {
            "bucket": "2026-09-21T15:00:00",
            "count": 5,
            "phase": "tarde",
        }
        assert body["buckets"][1]["count"] == 3
        assert body["buckets"][1]["phase"] == "tarde"
        assert len(db_mock.execute.await_args_list) == 5

    def test_hour_buckets_phase_null_when_no_event_day(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        bucket = datetime(2026, 9, 21, 23, 0)
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([SimpleNamespace(bucket=bucket, count=2)]),
            _scalars_result([]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/temporal_distribution",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["buckets"] == [
            {"bucket": "2026-09-21T23:00:00", "count": 2, "phase": None}
        ]
        assert len(db_mock.execute.await_args_list) == 3

    def test_day_granularity_no_phase_queries(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        day_bucket = datetime(2026, 9, 21, 0, 0)
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([SimpleNamespace(bucket=day_bucket, count=7)]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/temporal_distribution",
            params={"granularity": "day"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["granularity"] == "day"
        assert body["buckets"] == [
            {"bucket": "2026-09-21T00:00:00", "count": 7, "phase": None}
        ]
        assert len(db_mock.execute.await_args_list) == 2

    def test_service_category_filter_pass_through(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        bucket = datetime(2026, 9, 21, 15, 0)
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([SimpleNamespace(bucket=bucket, count=1)]),
            _scalars_result([]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/temporal_distribution",
            params={"service_category": "parking"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["service_category"] == "parking"

    def test_invalid_timezone_400(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/temporal_distribution",
            params={"timezone": "Not/AZone"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid timezone"
        assert not db_mock.execute.await_args_list

    def test_invalid_granularity_422(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/temporal_distribution",
            params={"granularity": "week"},
            headers=auth_headers,
        )
        assert resp.status_code == 422


class TestRecommendedZones:
    def test_zones_expanded_and_sorted_by_recommendations(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result(
                [
                    SimpleNamespace(
                        zone_id="z-gastro-1",
                        zone_name="Paseo de las Artes",
                        zone_type="gastronomy",
                        recommendations=12,
                    ),
                    SimpleNamespace(
                        zone_id="z-parking-1",
                        zone_name="Estacionamiento Norte",
                        zone_type="parking",
                        recommendations=4,
                    ),
                ]
            ),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/recommended_zones",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["event_id"] == EVENT_ID
        assert body["zones"] == [
            {
                "zone_id": "z-gastro-1",
                "zone_name": "Paseo de las Artes",
                "zone_type": "gastronomy",
                "recommendations": 12,
            },
            {
                "zone_id": "z-parking-1",
                "zone_name": "Estacionamiento Norte",
                "zone_type": "parking",
                "recommendations": 4,
            },
        ]
        assert len(db_mock.execute.await_args_list) == 2

    def test_zones_empty_without_data(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/recommended_zones",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["zones"] == []

    def test_service_category_filter_pass_through(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/recommended_zones",
            params={"service_category": "bathroom"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["service_category"] == "bathroom"