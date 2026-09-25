"""Tests del endpoint ``/operational_profile`` (ETAPA 5).

Simula por completo el acceso a BD (``get_async_db`` override con
``AsyncMock.execute.side_effect`` en el orden exacto de consultas del
endpoint) y valida: autenticación JWT, hallazgo de evento, el contrato de
respuesta con los 4 bloques (platform/predictions/observations/events), la
resolución de fase por minuto local con bisect, el fallback de
``operational_phases`` por id faltante y las notas de ``insufficient_data``.
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

EVENT_ID = "test-event-1"
ARGENTINA = "America/Argentina/Buenos_Aires"
PROFILE_ID = "00000000-0000-0000-0000-00000000000a"
PHASE_TARDE = "00000000-0000-0000-0000-000000000001"
PHASE_OTRA = "00000000-0000-0000-0000-000000000002"
ZONE_1 = "z-escenario-norte"


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


def _utc(y, mo, d, h, mi):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


def _compiled(db_mock: AsyncMock, index: int) -> tuple[str, dict]:
    stmt = db_mock.execute.await_args_list[index].args[0]
    compiled = stmt.compile()
    return str(compiled), dict(compiled.params)


def _flatten(values) -> list:
    flat: list = []
    for value in values:
        if isinstance(value, (list, tuple, set)):
            flat.extend(_flatten(value))
        else:
            flat.append(value)
    return flat


class TestOperationalProfileAuth:
    def test_401_without_token(self, client: TestClient, db_mock: AsyncMock):
        resp = client.get(f"/api/events/{EVENT_ID}/reports/operational_profile")
        assert resp.status_code == 401

    def test_404_event_not_found(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.return_value = _event_result(None)
        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/operational_profile",
            headers=auth_headers,
        )
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Event not found"

    def test_invalid_timezone_400(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/operational_profile",
            params={"timezone": "Not/AZone"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert resp.json()["detail"] == "Invalid timezone"
        assert not db_mock.execute.await_args_list


class TestOperationalProfileFullData:
    def test_full_flow_with_all_sources(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event()),
            _scalars_result(
                [
                    SimpleNamespace(
                        id="ed1",
                        date=date(2026, 9, 20),
                        operational_profile_id=PROFILE_ID,
                    )
                ]
            ),
            _scalars_result(
                [
                    SimpleNamespace(
                        event_day_id="ed1",
                        operational_phase_id=PHASE_TARDE,
                        start_min=900,
                        end_min=1260,
                    )
                ]
            ),
            _scalars_result(
                [SimpleNamespace(id=PHASE_TARDE, name="tarde", sort_order=1)]
            ),
            _scalars_result(
                [
                    SimpleNamespace(
                        event_day_id="ed1",
                        active_phase_id=PHASE_TARDE,
                        timestamp=_utc(2026, 9, 20, 18, 0),
                        zone_states_data=[
                            {
                                "zone_id": ZONE_1,
                                "projected_density": 42,
                                "operational_state": "moderado",
                            }
                        ],
                    ),
                    SimpleNamespace(
                        event_day_id="ed1",
                        active_phase_id=PHASE_TARDE,
                        timestamp=_utc(2026, 9, 20, 19, 0),
                        zone_states_data=[
                            {
                                "zone_id": ZONE_1,
                                "projected_density": 50,
                                "operational_state": "alto",
                            }
                        ],
                    ),
                ]
            ),
            _scalars_result(
                [
                    SimpleNamespace(
                        event_day_id="ed1",
                        zone_id=ZONE_1,
                        timestamp=_utc(2026, 9, 20, 19, 0),
                        observed_density=5,
                    ),
                    SimpleNamespace(
                        event_day_id="ed1",
                        zone_id=ZONE_1,
                        timestamp=_utc(2026, 9, 20, 20, 0),
                        observed_density=7,
                    ),
                ]
            ),
            _scalars_result(
                [
                    SimpleNamespace(
                        id="op-ev-1",
                        event_day_id="ed1",
                        zone_id=ZONE_1,
                        event_type="overcrowding",
                        is_incident=True,
                        start_timestamp=_utc(2026, 9, 20, 18, 30),
                        end_timestamp=_utc(2026, 9, 20, 20, 0),
                        description="Zona límite de capacidad",
                    )
                ]
            ),
            _scalars_result([SimpleNamespace(id=ZONE_1, name="Escenario Norte")]),
            _all_result(
                [
                    SimpleNamespace(
                        hour=datetime(2026, 9, 20, 16, 0),
                        service_category="parking",
                        result_status="ok",
                        count=4,
                    ),
                    SimpleNamespace(
                        hour=datetime(2026, 9, 20, 17, 0),
                        service_category="parking",
                        result_status="empty",
                        count=1,
                    ),
                    SimpleNamespace(
                        hour=datetime(2026, 9, 21, 3, 0),
                        service_category="parking",
                        result_status="error",
                        count=2,
                    ),
                ]
            ),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/operational_profile",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["event_id"] == EVENT_ID
        assert body["event_name"] == "Festival de la Primavera 2026"
        assert body["timezone"] == ARGENTINA
        assert body["operational_profile_id"] == PROFILE_ID
        assert len(db_mock.execute.await_args_list) == 9

        assert body["phases"] == [
            {
                "phase_id": PHASE_TARDE,
                "phase_name": "tarde",
            },
            {
                "phase_id": None,
                "phase_name": "unassigned",
            },
        ]

        platform = {p["phase_id"]: p for p in body["platform_queries"]}
        assert platform[PHASE_TARDE] == {
            "phase_id": PHASE_TARDE,
            "phase_name": "tarde",
            "consultas_total": 5,
            "with_results": 4,
            "empty": 1,
            "unavailable": 0,
            "error": 0,
        }
        assert platform[None] == {
            "phase_id": None,
            "phase_name": "unassigned",
            "consultas_total": 2,
            "with_results": 0,
            "empty": 0,
            "unavailable": 0,
            "error": 2,
        }

        predictions = body["predictions_summary"]
        assert len(predictions) == 1
        assert predictions[0]["phase_id"] == PHASE_TARDE
        assert predictions[0]["predictions_count"] == 2
        assert predictions[0]["zones"] == [
            {
                "zone_id": ZONE_1,
                "zone_name": "Escenario Norte",
                "projected_density": 50,
                "operational_state": "alto",
            }
        ]

        observations = body["observations_summary"]
        assert len(observations) == 1
        assert observations[0]["phase_id"] == PHASE_TARDE
        assert observations[0]["observations_count"] == 2
        assert observations[0]["zones"] == [
            {
                "zone_id": ZONE_1,
                "zone_name": "Escenario Norte",
                "observations_count": 2,
                "observed_density_total": 12,
                "observed_density_avg": 6.0,
            }
        ]

        events = body["operational_events_summary"]
        assert len(events) == 1
        assert events[0]["phase_id"] == PHASE_TARDE
        assert events[0]["total_events"] == 1
        assert events[0]["incidents"] == 1
        assert events[0]["events"][0]["operational_event_id"] == "op-ev-1"
        assert events[0]["events"][0]["zone_name"] == "Escenario Norte"

        assert body["insufficient_data"] == [
            "2 actividades de usuario sin fase asignada (fuera de ventana operativa)."
        ]

    def test_operational_phases_fallback_by_missing_id(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event()),
            _scalars_result(
                [
                    SimpleNamespace(
                        id="ed1",
                        date=date(2026, 9, 20),
                        operational_profile_id=PROFILE_ID,
                    )
                ]
            ),
            _scalars_result(
                [
                    SimpleNamespace(
                        event_day_id="ed1",
                        operational_phase_id=PHASE_OTRA,
                        start_min=480,
                        end_min=720,
                    )
                ]
            ),
            _scalars_result(
                [SimpleNamespace(id=PHASE_TARDE, name="tarde", sort_order=1)]
            ),
            _scalars_result(
                [
                    SimpleNamespace(
                        event_day_id="ed1",
                        active_phase_id=PHASE_OTRA,
                        timestamp=_utc(2026, 9, 20, 10, 0),
                        zone_states_data=[],
                    )
                ]
            ),
            _scalars_result(
                [SimpleNamespace(id=PHASE_OTRA, name="mañana", sort_order=0)]
            ),
            _scalars_result([]),
            _scalars_result([]),
            _scalars_result([SimpleNamespace(id=ZONE_1, name="Escenario Norte")]),
            _all_result([]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/operational_profile",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(db_mock.execute.await_args_list) == 10
        assert body["predictions_summary"][0]["phase_name"] == "mañana"


class TestOperationalProfileNoData:
    def test_event_days_empty(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event()),
            _scalars_result([]),
            _scalars_result([SimpleNamespace(id=ZONE_1, name="Escenario Norte")]),
            _all_result([]),
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/operational_profile",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(db_mock.execute.await_args_list) == 4
        assert body["phases"] == []
        assert body["platform_queries"] == []
        assert body["predictions_summary"] == []
        assert body["observations_summary"] == []
        assert body["operational_events_summary"] == []
        assert body["operational_profile_id"] is None
        assert (
            "El evento no tiene jornadas operativas (event_days) configuradas."
            in body["insufficient_data"]
        )
        assert (
            "No hay predicciones persistidas para las jornadas del evento."
            in body["insufficient_data"]
        )
        assert (
            "No hay observaciones operativas para relacionar."
            in body["insufficient_data"]
        )
        assert "No hay eventos operativos registrados." in body["insufficient_data"]


class TestOperationalProfilePeriod:
    """``operational_profile`` respeta el mismo período efectivo que ETAPA 2."""

    EVENT_START = _utc(2026, 9, 20, 12, 0)
    EVENT_END = _utc(2026, 9, 22, 23, 59)

    def _side_effect(self, event):
        return [
            _event_result(event),
            _scalars_result([]),
            _scalars_result([SimpleNamespace(id=ZONE_1, name="Escenario Norte")]),
            _all_result([]),
        ]

    def test_accumulated_mode_declared_and_unfiltered(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = self._side_effect(_event())

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/operational_profile",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["period"] == {"start": None, "end": None, "mode": "accumulated"}
        agg_sql, _ = _compiled(db_mock, 3)
        assert "timestamp >=" not in agg_sql
        assert "timestamp <=" not in agg_sql
        days_sql, _ = _compiled(db_mock, 1)
        assert "event_days.date >=" not in days_sql
        assert "event_days.date <=" not in days_sql

    def test_event_period_declared_and_applied(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = self._side_effect(
            _event(self.EVENT_START, self.EVENT_END)
        )

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/operational_profile",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["period"] == {
            "start": self.EVENT_START.isoformat().replace("+00:00", "Z"),
            "end": self.EVENT_END.isoformat().replace("+00:00", "Z"),
            "mode": "event",
        }
        agg_sql, agg_params = _compiled(db_mock, 3)
        assert "timestamp >=" in agg_sql
        assert "timestamp <=" in agg_sql
        assert self.EVENT_START in agg_params.values()
        assert self.EVENT_END in agg_params.values()
        assert "interaction_type IN" in agg_sql
        assert "origin" in agg_sql

    def test_explicit_period_declared_and_applied(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        start = _utc(2026, 9, 21, 0, 0)
        end = _utc(2026, 9, 21, 23, 59)
        db_mock.execute.side_effect = self._side_effect(
            _event(self.EVENT_START, self.EVENT_END)
        )

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/operational_profile",
            params={"start": start.isoformat(), "end": end.isoformat()},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["period"]["mode"] == "requested"
        assert body["period"]["start"].startswith("2026-09-21T00:00:00")
        assert body["period"]["end"].startswith("2026-09-21T23:59:00")
        agg_sql, agg_params = _compiled(db_mock, 3)
        assert start in agg_params.values()
        assert end in agg_params.values()
        assert self.EVENT_START not in agg_params.values()
        assert self.EVENT_END not in agg_params.values()

    def test_event_days_scoped_to_period_local_dates(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        start = _utc(2026, 9, 21, 3, 0)
        end = _utc(2026, 9, 21, 23, 0)
        db_mock.execute.side_effect = self._side_effect(
            _event(self.EVENT_START, self.EVENT_END)
        )

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/operational_profile",
            params={"start": start.isoformat(), "end": end.isoformat()},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        days_sql, days_params = _compiled(db_mock, 1)
        assert "event_days.date >=" in days_sql
        assert "event_days.date <=" in days_sql
        assert date(2026, 9, 21) in days_params.values()

    def test_open_ended_period_scopes_only_declared_side(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        start = _utc(2026, 9, 21, 3, 0)
        db_mock.execute.side_effect = self._side_effect(
            _event(self.EVENT_START, self.EVENT_END)
        )

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/operational_profile",
            params={"start": start.isoformat()},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["period"]["mode"] == "requested"
        assert body["period"]["end"] is None
        agg_sql, _ = _compiled(db_mock, 3)
        assert "timestamp >=" in agg_sql
        assert "timestamp <=" not in agg_sql
        days_sql, _ = _compiled(db_mock, 1)
        assert "event_days.date >=" in days_sql
        assert "event_days.date <=" not in days_sql

    def test_event_days_not_scoped_in_accumulated_mode(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = self._side_effect(_event())

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/operational_profile",
            params={"timezone": ARGENTINA},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        days_sql, days_params = _compiled(db_mock, 1)
        assert "event_days.date" in days_sql
        assert not any(isinstance(v, date) for v in days_params.values())

    def test_observaciones_y_predicciones_se_acotan_a_las_jornadas_del_periodo(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        """Una jornada fuera del período no puede aportar observaciones.

        El endpoint acota EventDay por fecha local y de ahí se derivan los
        ``event_day_id`` que alimentan predicciones, observaciones y eventos
        operativos. Si la jornada Historical queda fuera, sus observaciones no
        se cargan, aunque pertenezcan al mismo evento.
        """
        start = _utc(2026, 9, 25, 3, 0)
        end = _utc(2026, 9, 26, 2, 59)
        db_mock.execute.side_effect = [
            _event_result(_event(self.EVENT_START, self.EVENT_END)),
            # Solo la jornada del período: la histórica queda fuera.
            _scalars_result(
                [SimpleNamespace(id="ed-25", date=date(2026, 9, 25), operational_profile_id=None)]
            ),
            _scalars_result([]),  # event_day_phases
            _scalars_result([]),  # predictions
            _scalars_result(
                [
                    SimpleNamespace(
                        event_day_id="ed-25",
                        zone_id=ZONE_1,
                        timestamp=_utc(2026, 9, 25, 12, 0),
                        observed_density=10.0,
                    )
                ]
            ),  # observations
            _scalars_result([]),  # operational_events
            _scalars_result([]),  # zones
            _all_result([]),  # actividad
        ]

        resp = client.get(
            f"/api/events/{EVENT_ID}/reports/operational_profile",
            params={"start": start.isoformat(), "end": end.isoformat()},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        # La consulta de jornadas queda acotada a la ventana local.
        _days_sql, days_params = _compiled(db_mock, 1)
        flat = _flatten(days_params.values())
        assert date(2026, 9, 25) in flat
        assert date(2026, 7, 15) not in flat

        # Observaciones y predicciones solo consultedan las jornadas devueltas.
        for index in (3, 4, 5):
            sql, params = _compiled(db_mock, index)
            assert "event_day_id IN" in sql
            values = _flatten(params.values())
            assert "ed-25" in values
            assert "ed-historico" not in values