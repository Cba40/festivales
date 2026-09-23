"""Tests de los endpoints get de informes municipales base (ETAPA 3).

El acceso a BD se simula por completo (misma técnica que
``test_analytics_evaluate.py``): se valida el contrato HTTP, la
autenticación JWT existente y la lógica de agregaciones.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.db.session import get_async_db
from app.main import app

ENDPOINT = "/api/events/{event_id}/reports/{report}"
EVENT_ID = "test-event-1"
EVENT_START = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
EVENT_END = datetime(2026, 9, 22, 23, 59, tzinfo=timezone.utc)

REPORTS = ["summary", "service_breakdown", "coverage_gaps", "technical_incidents"]


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


class TestAuth:
    @pytest.mark.parametrize("report", REPORTS)
    def test_401_without_token(self, client: TestClient, db_mock: AsyncMock, report: str):
        resp = client.get(f"/api/events/{EVENT_ID}/reports/{report}")
        assert resp.status_code == 401

    @pytest.mark.parametrize("report", REPORTS)
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


class TestSummary:
    def test_summary_derives_period_from_event_dates(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([("ok", 5), ("empty", 3), ("error", 2), ("unavailable", 1)]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["event_id"] == EVENT_ID
        assert body["event_name"] == "Festival de la Primavera 2026"
        assert _parse_iso(body["period"]["start"]) == EVENT_START
        assert _parse_iso(body["period"]["end"]) == EVENT_END
        assert body["total_consultas"] == 11
        assert body["with_results"] == 5
        assert body["coverage_gaps_empty"] == 3
        assert body["technical_errors"] == 2
        assert body["breakdown"] == [
            {"result_status": "ok", "count": 5},
            {"result_status": "empty", "count": 3},
            {"result_status": "unavailable", "count": 1},
            {"result_status": "error", "count": 2},
        ]

    def test_summary_falls_back_to_log_min_max(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        min_ts = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)
        max_ts = datetime(2026, 9, 21, 22, 0, tzinfo=timezone.utc)
        db_mock.execute.side_effect = [
            _event_result(_event(None, None)),
            _one_result((min_ts, max_ts)),
            _all_result([("ok", 4), ("error", 1)]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert _parse_iso(body["period"]["start"]) == min_ts
        assert _parse_iso(body["period"]["end"]) == max_ts
        assert body["total_consultas"] == 5
        assert body["with_results"] == 4
        assert body["technical_errors"] == 1
        assert body["coverage_gaps_empty"] == 0

    def test_summary_explicit_period_params(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        start = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 9, 21, 23, 59, tzinfo=timezone.utc)
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([("ok", 2)]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/summary",
            params={"start": start.isoformat(), "end": end.isoformat()},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert _parse_iso(body["period"]["start"]) == start
        assert _parse_iso(body["period"]["end"]) == end
        assert body["total_consultas"] == 2
        assert len(db_mock.execute.await_args_list) == 2


class TestServiceBreakdown:
    def test_percentage_of_registered_consultas(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result(
                [
                    SimpleNamespace(service_category="gastronomy", total_consultas=6),
                    SimpleNamespace(service_category="parking", total_consultas=4),
                ]
            ),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/service_breakdown",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["services"] == [
            {"service_category": "gastronomy", "total_consultas": 6, "percentage": 60.0},
            {"service_category": "parking", "total_consultas": 4, "percentage": 40.0},
        ]

    def test_zero_consultas_zero_percentage(
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
            f"/api/events/{EVENT_ID}/reports/service_breakdown",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["services"] == []


class TestCoverageGaps:
    def test_empty_gaps_per_service_and_temporal(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        day_1 = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)
        day_2 = datetime(2026, 9, 22, 0, 0, tzinfo=timezone.utc)
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result(
                [
                    SimpleNamespace(service_category="bathroom", total_consultas=10, empty_count=7),
                    SimpleNamespace(service_category="parking", total_consultas=5, empty_count=1),
                ]
            ),
            _all_result(
                [
                    SimpleNamespace(day=day_1, count=5),
                    SimpleNamespace(day=day_2, count=3),
                ]
            ),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/coverage_gaps",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["services"] == [
            {"service_category": "bathroom", "total_consultas": 10, "empty_count": 7, "empty_rate": 0.7},
            {"service_category": "parking", "total_consultas": 5, "empty_count": 1, "empty_rate": 0.2},
        ]
        assert body["temporal_distribution"] == [
            {"day": "2026-09-21", "count": 5},
            {"day": "2026-09-22", "count": 3},
        ]


class TestTechnicalIncidents:
    def test_errors_per_service_and_temporal(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        day_1 = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result(
                [
                    SimpleNamespace(service_category="transport", total_consultas=8, error_count=2),
                    SimpleNamespace(service_category="exit", total_consultas=10, error_count=0),
                ]
            ),
            _all_result(
                [
                    SimpleNamespace(day=day_1, count=2),
                ]
            ),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/technical_incidents",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["services"] == [
            {"service_category": "transport", "error_count": 2, "error_rate": 0.25},
            {"service_category": "exit", "error_count": 0, "error_rate": 0.0},
        ]
        assert body["temporal_distribution"] == [{"day": "2026-09-21", "count": 2}]
