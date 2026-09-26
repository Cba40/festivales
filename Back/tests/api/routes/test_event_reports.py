"""Tests de los endpoints get de informes municipales base (ETAPA 3).

El acceso a BD se simula por completo (misma técnica que
``test_analytics_evaluate.py``): se valida el contrato HTTP, la
autenticación JWT existente y la lógica de agregaciones.
"""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import re

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import func, join, select

from app.core.config import settings
from app.db.session import get_async_db
from app.main import app
from app.models.service_interaction_log import ServiceInteractionLog
from app.models.zone import Zone

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


def _scalars_result(rows):
    res = MagicMock()
    res.scalars.return_value.all.return_value = rows
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
            _all_result([]),
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
            _all_result([]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/service_breakdown",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["services"] == []


class TestServiceBreakdownFilters:
    """El desglose por request_mode expone los filtros que el usuario aplicó."""

    def test_desglosa_por_request_mode(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([SimpleNamespace(service_category="exit", total_consultas=7)]),
            _all_result(
                [
                    SimpleNamespace(request_mode="mode=peatonal", total=4),
                    SimpleNamespace(request_mode="mode=vehicular", total=2),
                    SimpleNamespace(request_mode=None, total=1),
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
            {"service_category": "exit", "total_consultas": 7, "percentage": 100.0}
        ]
        assert body["filters"] == [
            {"request_mode": "mode=peatonal", "total": 4},
            {"request_mode": "mode=vehicular", "total": 2},
            {"request_mode": None, "total": 1},
        ]

    def test_desglose_usa_el_periodo_efectivo(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        start = datetime(2026, 9, 25, 3, 0, tzinfo=timezone.utc)
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([]),
            _all_result([SimpleNamespace(request_mode="type=hotel", total=3)]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/service_breakdown",
            params={"start": start.isoformat()},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        sql, params = _compiled(db_mock, 2)
        assert "request_mode" in sql
        assert "timestamp >=" in sql
        assert "timestamp <=" not in sql
        assert start in params.values()

    def test_sin_datos_devuelve_lista_vacia(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([]),
            _all_result([]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/service_breakdown",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["filters"] == []

    def test_respuesta_conserva_los_campos_previos(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([SimpleNamespace(service_category="gastronomy", total_consultas=5)]),
            _all_result([]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/service_breakdown",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["event_id"] == EVENT_ID
        assert body["event_name"] == "Festival de la Primavera 2026"
        assert body["period"]["mode"] == "event"
        assert body["services"][0]["percentage"] == 100.0


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


class TestCoverageGapsOriginAndTimezone:
    """El bloque de cobertura filtra por origen y bucketea en hora local."""

    def _side_effect(self):
        return [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result(
                [
                    SimpleNamespace(
                        service_category="bathroom", total_consultas=10, empty_count=7
                    ),
                ]
            ),
            _all_result([SimpleNamespace(day=date(2026, 7, 21), count=7)]),
        ]

    def test_sin_origin_no_agrega_predicado_de_origen(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = self._side_effect()

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/coverage_gaps",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        for index in (1, 2):
            sql, _params = _compiled(db_mock, index)
            assert "origin" not in sql

    def test_filtra_por_origin_user(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = self._side_effect()

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/coverage_gaps",
            params={"origin": "user"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        for index in (1, 2):
            sql, params = _compiled(db_mock, index)
            assert "origin" in sql
            assert "user" in params.values()

    @pytest.mark.parametrize("origin", ["prefetch", "system"])
    def test_filtra_por_cualquier_origin_valido(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
        origin: str,
    ):
        db_mock.execute.side_effect = self._side_effect()

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/coverage_gaps",
            params={"origin": origin},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        _sql, params = _compiled(db_mock, 1)
        assert origin in params.values()

    def test_rechaza_origin_invalido(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/coverage_gaps",
            params={"origin": "inventado"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_rechaza_timezone_invalida(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/coverage_gaps",
            params={"timezone": "Not/AZone"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_bucketing_diario_usa_zona_local(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = self._side_effect()

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/coverage_gaps",
            params={"timezone": "America/Argentina/Buenos_Aires"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        sql, params = _compiled(db_mock, 2)
        # El día se trunca en hora local: un request de las 23:00 ART pertenece a
        # su día local y no al siguiente por usar UTC.
        assert "AT TIME ZONE" in sql
        assert "America/Argentina/Buenos_Aires" in params.values()
        assert "date_trunc" in sql
        # La agregación por categoría no lleva bucketing temporal.
        first_sql, _ = _compiled(db_mock, 1)
        assert "AT TIME ZONE" not in first_sql

    def test_los_totales_no_cambian_con_origin_ni_timezone(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = self._side_effect()

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/coverage_gaps",
            params={"origin": "system", "timezone": "UTC"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["services"] == [
            {
                "service_category": "bathroom",
                "total_consultas": 10,
                "empty_count": 7,
                "empty_rate": 0.7,
            }
        ]
        assert body["temporal_distribution"] == [{"day": "2026-07-21", "count": 7}]


class TestTemporalDistributionRequestModeBreakdown:
    """El detalle por request_mode solo se calcula al filtrar por categoría."""

    BUCKET_1 = datetime(2026, 9, 26, 8, 0)
    BUCKET_2 = datetime(2026, 9, 26, 17, 0)

    URL = f"/api/events/{EVENT_ID}/reports/temporal_distribution"

    def _agg(self):
        return _all_result(
            [
                SimpleNamespace(bucket=self.BUCKET_1, count=2),
                SimpleNamespace(bucket=self.BUCKET_2, count=1),
            ]
        )

    def test_incluye_desglose_cuando_filtra_categoria(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            self._agg(),
            _all_result(
                [
                    SimpleNamespace(
                        bucket=self.BUCKET_1,
                        request_mode="transporte_interurbano=Córdoba",
                        count=1,
                    ),
                    SimpleNamespace(
                        bucket=self.BUCKET_1,
                        request_mode="transporte_urbano=Los Nogales",
                        count=1,
                    ),
                    SimpleNamespace(
                        bucket=self.BUCKET_2,
                        request_mode="transporte_interurbano=Córdoba",
                        count=1,
                    ),
                ]
            ),
            _scalars_result([]),
        ]

        resp = client.get(
            self.URL,
            params={"granularity": "hour", "service_category": "transport"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        buckets = resp.json()["buckets"]

        assert buckets[0]["count"] == 2
        assert buckets[0]["breakdown"] == [
            {"request_mode": "transporte_interurbano=Córdoba", "count": 1},
            {"request_mode": "transporte_urbano=Los Nogales", "count": 1},
        ]
        assert buckets[1]["breakdown"] == [
            {"request_mode": "transporte_interurbano=Córdoba", "count": 1}
        ]

    def test_sin_desglose_sin_filtro_de_categoria(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            self._agg(),
            _scalars_result([]),
        ]

        resp = client.get(
            self.URL,
            params={"granularity": "hour"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        for bucket in resp.json()["buckets"]:
            assert bucket["breakdown"] is None

    def test_no_consulta_el_desglose_si_no_filtra_categoria(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            self._agg(),
            _scalars_result([]),
        ]

        resp = client.get(
            self.URL,
            params={"granularity": "hour"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        # event + agregación + EventDay: la consulta de detalle no se ejecuta.
        assert db_mock.execute.await_count == 3

    def test_desglose_agrupado_por_bucket_y_request_mode(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            self._agg(),
            _all_result([]),
            _scalars_result([]),
        ]

        resp = client.get(
            self.URL,
            params={"granularity": "hour", "service_category": "transport"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        sql, params = _compiled(db_mock, 2)
        assert "service_interaction_log.request_mode" in sql
        assert "request_mode" in sql
        assert params["service_category_1"] == "transport"
        # Sigue acotado a la actividad de usuario.
        assert params["interaction_type_1"] == ["screen_open", "filter_change"]
        assert params["origin_1"] == "user"

    def test_desglose_por_dia_tambien_se_emite(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([SimpleNamespace(bucket=self.BUCKET_1, count=1)]),
            _all_result(
                [
                    SimpleNamespace(
                        bucket=self.BUCKET_1,
                        request_mode="zona=Estacionamiento Central",
                        count=1,
                    )
                ]
            ),
        ]

        resp = client.get(
            self.URL,
            params={"granularity": "day", "service_category": "parking"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["buckets"][0]["breakdown"] == [
            {"request_mode": "zona=Estacionamiento Central", "count": 1}
        ]

    def test_bucket_sin_desglose_devuelve_none(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            self._agg(),
            _all_result(
                [
                    SimpleNamespace(
                        bucket=self.BUCKET_1,
                        request_mode="transporte_interurbano=Córdoba",
                        count=1,
                    )
                ]
            ),
            _scalars_result([]),
        ]

        resp = client.get(
            self.URL,
            params={"granularity": "hour", "service_category": "transport"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        buckets = resp.json()["buckets"]
        # BUCKET_1 tiene 2 eventos pero el desglose mockeado solo reporta 1: el
        # contrato no inventa datos, expone lo que devolvió la consulta.
        assert buckets[0]["breakdown"] == [
            {"request_mode": "transporte_interurbano=Córdoba", "count": 1}
        ]
        assert buckets[1]["breakdown"] is None


class TestTemporalDistributionBreakdownSumsToCount:
    """Invariante: la suma del desglose por bucket debe igualar su conteo."""

    def test_suma_coincide_con_el_total_del_bucket(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        rows = [
            ("transporte_interurbano=Córdoba", 3),
            ("transporte_urbano=Los Nogales", 1),
            ("transporte_urbano=Córdoba", 2),
        ]
        bucket = datetime(2026, 9, 26, 17, 0)
        total = sum(count for _, count in rows)
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([SimpleNamespace(bucket=bucket, count=total)]),
            _all_result(
                [SimpleNamespace(bucket=bucket, request_mode=mode, count=count) for mode, count in rows]
            ),
            _scalars_result([]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/temporal_distribution",
            params={"granularity": "hour", "service_category": "transport"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["buckets"][0]
        assert sum(item["count"] for item in data["breakdown"]) == data["count"]
        assert data["count"] == 6


class TestZoneAnalysis:
    """Combina demanda real (`filter_change` + `zona=`) y cobertura (`zone_ids`).

    El endpoint resuelve ambas métricas en UNA consulta con LEFT JOIN desde
    ``zones``, así que el mock entrega una sola lista de filas ya unificadas.
    """

    URL = f"/api/events/{EVENT_ID}/reports/zone_analysis"

    def _zones(self, rows):
        return _all_result(
            [
                SimpleNamespace(
                    zone_id=zone_id,
                    zone_name=name,
                    zone_type=zone_type,
                    real_choices=real_choices,
                    recommendation_count=count,
                    avg_position=avg_position,
                )
                for zone_id, name, zone_type, real_choices, count, avg_position in rows
            ]
        )

    def test_une_demanda_y_cobertura(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            self._zones(
                [
                    ("zA", "Estacionamiento Norte", "parking", 7, 392, 1.2),
                    ("zB", "Estacionamiento Sur", "parking", 2, 392, 3.8),
                    ("zC", "Baños Centro", "bathroom", 0, 385, 2.0),
                ]
            ),
        ]

        resp = client.get(self.URL, headers=auth_headers)
        assert resp.status_code == 200
        zones = {z["zone_id"]: z for z in resp.json()["zones"]}

        assert zones["zA"] == {
            "zone_id": "zA",
            "zone_name": "Estacionamiento Norte",
            "zone_type": "parking",
            "real_choices": 7,
            "recommendation_count": 392,
            "avg_position": 1.2,
        }
        assert zones["zB"]["real_choices"] == 2
        # zC solo tiene cobertura: fue recomendada pero nunca elegida.
        assert zones["zC"]["real_choices"] == 0
        assert zones["zC"]["recommendation_count"] == 385

    def test_zona_con_demanda_sin_cobertura_no_se_descarta(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        """Regresión del bug de intersección.

        Armar la respuesta iterando solo la cobertura perdía las zonas que los
        usuarios eligieron pero que el sistema no recomendó dentro del período
        (típico de una zona recomendada antes de la ventana consultada). Con el
        LEFT JOIN aparecen con ``recommendation_count=0`` y ``avg_position`` nulo.
        """
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            self._zones(
                [
                    ("zElegida", "Elegida sin oferta", "parking", 5, 0, None),
                    ("zTop", "Siempre primera", "parking", 0, 50, 1.0),
                ]
            ),
        ]

        resp = client.get(self.URL, headers=auth_headers)
        assert resp.status_code == 200
        zones = {z["zone_id"]: z for z in resp.json()["zones"]}

        # La zona elegida existe en la respuesta pese a no tener cobertura.
        assert zones["zElegida"] == {
            "zone_id": "zElegida",
            "zone_name": "Elegida sin oferta",
            "zone_type": "parking",
            "real_choices": 5,
            "recommendation_count": 0,
            "avg_position": None,
        }
        assert zones["zTop"]["real_choices"] == 0

    def test_consulta_usa_left_join_para_la_union(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        """La unión tiene que resolverse en SQL, no en Python.

        ``INNER JOIN`` o un recorrido post-hoc de la cobertura vuelven a perder
        las zonas sin oferta en la ventana.
        """
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            self._zones([]),
        ]

        resp = client.get(self.URL, headers=auth_headers)
        assert resp.status_code == 200

        sql, _ = _compiled(db_mock, 1)
        assert sql.count("LEFT OUTER JOIN") == 2
        # La recorte final deja fuera las zonas sin nada que mostrar.
        assert "coalesce(" in sql
        assert "zones.event_id" in sql

    def test_orden_por_demanda_luego_posicion(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            self._zones(
                [
                    ("zA", "A", "parking", 5, 10, 4.0),
                    ("zB", "B", "parking", 1, 10, 1.0),
                    ("zC", "C", "parking", 0, 10, 2.0),
                ]
            ),
        ]

        resp = client.get(self.URL, headers=auth_headers)
        assert resp.status_code == 200
        # zA (5) arriba; después los que no tienen demanda, por posición.
        assert [z["zone_id"] for z in resp.json()["zones"]] == ["zA", "zB", "zC"]

    def test_zona_sin_posicion_queda_al_final(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            self._zones(
                [
                    ("zSinPos", "Nunca recomendada", "parking", 2, 0, None),
                    ("zTop", "Primera siempre", "parking", 0, 50, 1.0),
                ]
            ),
        ]

        resp = client.get(self.URL, headers=auth_headers)
        assert resp.status_code == 200
        # Demanda manda: zSinPos (2) va arriba aunque no tenga posición.
        assert [z["zone_id"] for z in resp.json()["zones"]] == ["zSinPos", "zTop"]
        assert resp.json()["zones"][0]["avg_position"] is None
        assert resp.json()["zones"][0]["recommendation_count"] == 0

    def test_consulta_de_demanda_usa_split_part_y_actividad(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            self._zones([]),
        ]

        resp = client.get(
            self.URL,
            params={"service_category": "parking"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        sql, params = _compiled(db_mock, 1)
        assert "split_part" in sql
        assert "request_mode LIKE" in sql
        # La demanda exige intención del usuario, no requests técnicas.
        assert params["interaction_type_1"] == ["screen_open", "filter_change"]
        assert params["origin_1"] == "user"
        assert params["service_category_1"] == "parking"

    def test_cobertura_usa_ordinality_y_acota_al_evento(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            self._zones([]),
        ]

        resp = client.get(self.URL, headers=auth_headers)
        assert resp.status_code == 200

        sql, _ = _compiled(db_mock, 1)
        assert "WITH ORDINALITY" in sql
        assert "jsonb_array_elements_text" in sql
        assert "avg(" in sql
        # La cobertura cuenta requests técnicas, y solo las zonas del evento.
        assert "request" in str(sql)
        assert "zones.event_id" in sql

    def test_ordinality_no_emite_alias_duplicado(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        """Regresión: el alias lo emite ``table_valued``, no el render.

        Si el ``@compiles`` incluye su propio ``AS t(...)``, ``table_valued``
        agrega ``AS anon_N`` detrás y Postgres responde
        ``syntax error at or near "AS"``.
        """
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            self._zones([]),
        ]

        resp = client.get(self.URL, headers=auth_headers)
        assert resp.status_code == 200

        sql, _ = _compiled(db_mock, 1)
        # Exactamente un alias propio de la función set-returning.
        assert sql.count("WITH ORDINALITY AS") == 1
        # Ningún alias inmediatamente seguido de otro sobre la misma función.
        assert re.search(r"WITH ORDINALITY AS \w+\s*(\([^)]*\))?\s*AS \w+", sql) is None

    def test_ordinality_sobrevive_al_calculo_de_cache_key(self):
        """Regresión: ``str(stmt.compile())`` pasa aunque falte ``clause_expr``.

        El engine real arma una clave de caché antes de ejecutar, y ese recorrido
        es el que revienta con ``AttributeError: ... has no attribute
        'clause_expr'`` si el ``FunctionElement`` no inicializó su estado interno.
        Compilar a mano no alcanza para detectarlo.
        """
        from app.api.routes.event_reports import _expanded_zone_positions

        expanded = _expanded_zone_positions(
            [ServiceInteractionLog.interaction_type == "request"]
        ).subquery()
        stmt = (
            select(Zone.id, func.avg(expanded.c.position).label("avg_position"))
            .select_from(join(Zone, expanded, Zone.id == expanded.c.zone_id))
            .group_by(Zone.id)
        )

        assert "WITH ORDINALITY" in str(stmt.compile())
        assert stmt._generate_cache_key() is not None

    def test_rechaza_periodo_naive(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            self.URL,
            params={"start": "2026-07-15T00:00:00", "end": "2026-07-21T00:00:00"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_sin_zonas_devuelve_lista_vacia(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            self._zones([]),
        ]

        resp = client.get(self.URL, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["zones"] == []


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
        "service_breakdown": 2,
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


class TestTechnicalReportsReturnEmptyOutsidePeriod:
    """Un período sin datos debe devolver cero, no el histórico del evento."""

    DAY = datetime(2026, 9, 25, 3, 0, tzinfo=timezone.utc)
    DAY_END = datetime(2026, 9, 26, 2, 59, 59, 999000, tzinfo=timezone.utc)

    def test_coverage_gaps_vacio_con_periodo_sin_datos(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([]),
            _all_result([]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/coverage_gaps",
            params={"start": self.DAY.isoformat(), "end": self.DAY_END.isoformat()},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["services"] == []
        assert body["temporal_distribution"] == []
        assert body["period"]["mode"] == "requested"
        for index in (1, 2):
            sql, params = _compiled(db_mock, index)
            assert "timestamp >=" in sql
            assert "timestamp <=" in sql
            assert self.DAY in params.values()

    def test_recommended_zones_vacio_con_periodo_sin_datos(
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
            params={"start": self.DAY.isoformat(), "end": self.DAY_END.isoformat()},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["zones"] == []
        sql, params = _compiled(db_mock, 1)
        assert "timestamp >=" in sql
        assert "timestamp <=" in sql
        assert self.DAY in params.values()
        assert self.DAY_END in params.values()

    def test_technical_reports_aceptan_rango_abierto_sin_fecha_final(
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
            params={"start": self.DAY.isoformat()},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["zones"] == []
        assert body["period"]["start"].startswith("2026-09-25T03:00:00")
        assert body["period"]["end"] is None
        sql, _params = _compiled(db_mock, 1)
        assert "timestamp >=" in sql
        assert "timestamp <=" not in sql
