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


def _compiled(db_mock: AsyncMock, index: int) -> tuple[str, dict]:
    stmt = db_mock.execute.await_args_list[index].args[0]
    compiled = stmt.compile()
    return str(compiled), dict(compiled.params)


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

    def test_summary_accumulated_mode_without_declared_period(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(None, None)),
            _all_result([("ok", 4), ("error", 1)]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["period"] == {"start": None, "end": None, "mode": "accumulated"}
        assert body["total_consultas"] == 5
        assert body["with_results"] == 4
        assert body["technical_errors"] == 1
        assert body["coverage_gaps_empty"] == 0
        assert len(db_mock.execute.await_args_list) == 2

    def test_summary_event_period_filters_rows(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([("ok", 7)]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["period"]["mode"] == "event"
        assert _parse_iso(body["period"]["start"]) == EVENT_START
        assert _parse_iso(body["period"]["end"]) == EVENT_END
        sql, params = _compiled(db_mock, 1)
        assert "timestamp >=" in sql
        assert "timestamp <=" in sql
        assert EVENT_START in params.values()
        assert EVENT_END in params.values()

    def test_summary_accumulated_mode_has_no_timestamp_predicate(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(None, None)),
            _all_result([("ok", 3)]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/summary",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        sql, params = _compiled(db_mock, 1)
        assert "timestamp >=" not in sql
        assert "timestamp <=" not in sql
        assert EVENT_ID in params.values()

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
        assert body["period"]["mode"] == "requested"
        assert body["total_consultas"] == 2
        assert len(db_mock.execute.await_args_list) == 2
        sql, params = _compiled(db_mock, 1)
        assert start in params.values()
        assert end in params.values()
        assert EVENT_START not in params.values()
        assert EVENT_END not in params.values()

    def test_summary_explicit_period_overrides_event_dates(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        start = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([("ok", 1)]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/summary",
            params={"start": start.isoformat()},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["period"]["mode"] == "requested"
        assert _parse_iso(body["period"]["start"]) == start
        assert body["period"]["end"] is None
        sql, params = _compiled(db_mock, 1)
        assert "timestamp >=" in sql
        assert "timestamp <=" not in sql
        assert start in params.values()
        assert EVENT_START not in params.values()
        assert EVENT_END not in params.values()


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


class TestEffectivePeriodIsShared:
    """El período efectivo_filters_ SQL y se publica en PeriodRange."""

    EMPTY_SIDE_EFFECT = {
        "summary": 1,
        "service_breakdown": 1,
        "coverage_gaps": 2,
        "technical_incidents": 2,
        "temporal_distribution": 1,
        "recommended_zones": 1,
    }

    EXTRA_PARAMS = {
        "temporal_distribution": {"granularity": "day"},
    }

    @pytest.mark.parametrize("report", sorted(EMPTY_SIDE_EFFECT))
    def test_event_period_declared_and_applied(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
        report: str,
    ):
        extra = self.EMPTY_SIDE_EFFECT[report]
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            *[_all_result([]) for _ in range(extra)],
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/{report}",
            params=self.EXTRA_PARAMS.get(report),
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["period"] == {
            "start": EVENT_START.isoformat().replace("+00:00", "Z"),
            "end": EVENT_END.isoformat().replace("+00:00", "Z"),
            "mode": "event",
        }
        for index in range(1, extra + 1):
            sql, params = _compiled(db_mock, index)
            assert "timestamp >=" in sql, report
            assert "timestamp <=" in sql, report
            assert EVENT_START in params.values(), report
            assert EVENT_END in params.values(), report

    @pytest.mark.parametrize("report", sorted(EMPTY_SIDE_EFFECT))
    def test_accumulated_mode_declared_and_applied(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
        report: str,
    ):
        extra = self.EMPTY_SIDE_EFFECT[report]
        db_mock.execute.side_effect = [
            _event_result(_event(None, None)),
            *[_all_result([]) for _ in range(extra)],
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/{report}",
            params=self.EXTRA_PARAMS.get(report),
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["period"] == {"start": None, "end": None, "mode": "accumulated"}
        for index in range(1, extra + 1):
            sql, _params = _compiled(db_mock, index)
            assert "timestamp >=" not in sql, report
            assert "timestamp <=" not in sql, report

    @pytest.mark.parametrize("report", sorted(EMPTY_SIDE_EFFECT))
    def test_explicit_period_declared_and_applied(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
        report: str,
    ):
        start = datetime(2026, 9, 21, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 9, 21, 23, 59, 59, tzinfo=timezone.utc)
        extra = self.EMPTY_SIDE_EFFECT[report]
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            *[_all_result([]) for _ in range(extra)],
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/{report}",
            params={**self.EXTRA_PARAMS.get(report, {}), "start": start.isoformat(), "end": end.isoformat()},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["period"]["mode"] == "requested"
        assert _parse_iso(body["period"]["start"]) == start
        assert _parse_iso(body["period"]["end"]) == end
        for index in range(1, extra + 1):
            sql, params = _compiled(db_mock, index)
            assert "timestamp >=" in sql, report
            assert "timestamp <=" in sql, report
            assert start in params.values(), report
            assert end in params.values(), report

    @pytest.mark.parametrize("report", sorted(EMPTY_SIDE_EFFECT))
    def test_no_period_resolution_query_against_measured_data(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
        report: str,
    ):
        extra = self.EMPTY_SIDE_EFFECT[report]
        db_mock.execute.side_effect = [
            _event_result(_event(None, None)),
            *[_all_result([]) for _ in range(extra)],
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/{report}",
            params=self.EXTRA_PARAMS.get(report),
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert len(db_mock.execute.await_args_list) == extra + 1
        first_sql, _ = _compiled(db_mock, 0)
        assert "FROM events" in first_sql
        for index in range(1, extra + 1):
            sql, _params = _compiled(db_mock, index)
            assert "min(" not in sql.lower(), report
            assert "max(" not in sql.lower(), report


class TestResolvePeriodUnit:
    def test_requested_wins_over_event(self):
        from app.api.routes.event_reports import _resolve_period

        start = datetime(2026, 9, 21, tzinfo=timezone.utc)
        event = _event(EVENT_START, EVENT_END)
        period = _resolve_period(event, start, None)
        assert period.start == start
        assert period.end is None
        assert period.mode == "requested"

    def test_event_used_when_no_params(self):
        from app.api.routes.event_reports import _resolve_period

        period = _resolve_period(_event(EVENT_START, EVENT_END), None, None)
        assert period.start == EVENT_START
        assert period.end == EVENT_END
        assert period.mode == "event"

    def test_accumulated_when_nothing_declared(self):
        from app.api.routes.event_reports import _resolve_period

        period = _resolve_period(_event(None, None), None, None)
        assert period.start is None
        assert period.end is None
        assert period.mode == "accumulated"

    def test_resolver_touches_no_database(self):
        import inspect

        from app.api.routes.event_reports import _resolve_period

        assert inspect.iscoroutinefunction(_resolve_period) is False
        assert "AsyncSession" not in inspect.signature(_resolve_period).parameters
