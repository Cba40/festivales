"""Coherencia temporal de ``temporal_distribution`` (ETAPA 5).

Fija el orden obligatorio: día/período local → instantes absolutos (UTC) →
filtro sobre ``timestamp`` (timestamptz) → agrupamiento y presentación en la
timezone local. Incluye el cruce de medianoche UTC: un bucket local del 20/07
a las 23:30 llega a Postgres como 21/07 02:30Z, pero debe seguir resolviéndose
contra ``EventDay.date`` = 20/07.

No usa base de datos: ``get_async_db`` se sustituye por ``AsyncMock`` y el SQL
se inspecciona compilado.
"""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.db.session import get_async_db
from app.main import app

EVENT_ID = "test-event-1"
ARGENTINA = "America/Argentina/Buenos_Aires"
ENDPOINT = f"/api/events/{EVENT_ID}/reports/temporal_distribution"
PHASE_TARDE = "00000000-0000-0000-0000-000000000001"

EVENT_START = datetime(2026, 7, 20, 0, 0, tzinfo=timezone.utc)
EVENT_END = datetime(2026, 7, 26, 23, 59, tzinfo=timezone.utc)


def _event(start_date=None, end_date=None):
    return SimpleNamespace(
        id=EVENT_ID,
        name="Festival Jesus Maria 2026",
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


def _local_day_bounds(day: date, tz_name: str = ARGENTINA) -> tuple[datetime, datetime]:
    """Equivalente Python del helper de frontend (ETAPA 4)."""
    tz = ZoneInfo(tz_name)
    start = datetime(day.year, day.month, day.day, 0, 0, 0, 0, tzinfo=tz)
    end = datetime(day.year, day.month, day.day, 23, 59, 59, 999000, tzinfo=tz)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


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


class TestLocalDayBecomesAbsoluteBounds:
    """Validación 1 y 2: el filtro cubre el día local completo en UTC."""

    def test_los_limites_absolutos_cubren_el_dia_local_completo(self):
        start, end = _local_day_bounds(date(2026, 7, 21))

        # 21/07 00:00 ART => 21/07 03:00Z (no 21/07 00:00Z).
        assert start == datetime(2026, 7, 21, 3, 0, tzinfo=timezone.utc)
        # 21/07 23:59:59.999 ART => 22/07 02:59:59.999Z.
        assert end == datetime(2026, 7, 22, 2, 59, 59, 999000, tzinfo=timezone.utc)

    def test_2330_local_del_20_cae_en_el_dia_20_y_no_en_el_21(self):
        start_20, end_20 = _local_day_bounds(date(2026, 7, 20))
        start_21, end_21 = _local_day_bounds(date(2026, 7, 21))

        row_2330 = datetime(2026, 7, 21, 2, 30, tzinfo=timezone.utc)  # 20/07 23:30 ART
        assert start_20 <= row_2330 <= end_20
        assert not (start_21 <= row_2330 <= end_21)
        assert row_2330.astimezone(ZoneInfo(ARGENTINA)).date() == date(2026, 7, 20)

    def test_0030_local_del_21_cae_en_el_dia_21_y_no_en_el_20(self):
        start_20, end_20 = _local_day_bounds(date(2026, 7, 20))
        start_21, end_21 = _local_day_bounds(date(2026, 7, 21))

        row_0030 = datetime(2026, 7, 21, 3, 30, tzinfo=timezone.utc)  # 21/07 00:30 ART
        assert start_21 <= row_0030 <= end_21
        assert not (start_20 <= row_0030 <= end_20)
        assert row_0030.astimezone(ZoneInfo(ARGENTINA)).date() == date(2026, 7, 21)

    def test_el_endpoint_filtra_por_los_limites_absolutos_del_dia_local(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        start, end = _local_day_bounds(date(2026, 7, 21))
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([SimpleNamespace(bucket=datetime(2026, 7, 21, 0, 0), count=2)]),
            _scalars_result([]),
        ]

        resp = client.get(
            ENDPOINT,
            params={
                "start": start.isoformat(),
                "end": end.isoformat(),
                "granularity": "day",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200
        sql, params = _compiled(db_mock, 1)
        assert "timestamp >=" in sql
        assert "timestamp <=" in sql
        assert start in params.values()
        assert end in params.values()


class TestBucketUsesLocalTimezone:
    """Validación 3: agrupar y presentar en la timezone local, no en UTC."""

    def test_bucket_agrupa_con_at_time_zone(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([]),
            _scalars_result([]),
        ]

        resp = client.get(
            ENDPOINT,
            params={"granularity": "hour", "timezone": ARGENTINA},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        sql, params = _compiled(db_mock, 1)
        assert "AT TIME ZONE" in sql
        assert ARGENTINA in params.values()
        assert "hour" in params.values()
        assert "day" not in params.values()

    def test_bucket_por_dia_agrupa_con_at_time_zone(
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
            ENDPOINT,
            params={"granularity": "day", "timezone": ARGENTINA},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        sql, params = _compiled(db_mock, 1)
        assert "AT TIME ZONE" in sql
        assert ARGENTINA in params.values()
        assert "day" in params.values()

    def test_la_respuesta_declara_la_timezone_usada(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([SimpleNamespace(bucket=datetime(2026, 7, 21, 15, 0), count=1)]),
            _scalars_result([]),
        ]

        resp = client.get(
            ENDPOINT, params={"timezone": ARGENTINA}, headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["timezone"] == ARGENTINA
        # El bucket viaja como hora local sin offset (ya truncado por la zona).
        assert body["buckets"][0]["bucket"] == "2026-07-21T15:00:00"


class TestPhaseResolutionUsesLocalDate:
    """El bucket se compara contra EventDay.date usando su fecha local."""

    def test_bucket_local_de_2330_resuelve_contra_el_dia_20(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        # El bucket que devuelve la BD ya es hora local: 20/07 23:30.
        # Su equivalente UTC es 21/07 02:30Z: si se comparara contra la fecha
        # UTC se buscaría el EventDay del 21 y la fase quedaría sin asignar.
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([SimpleNamespace(bucket=datetime(2026, 7, 20, 23, 30), count=4)]),
            _scalars_result(
                [SimpleNamespace(id="ed-20", date=date(2026, 7, 20))]
            ),
            _scalars_result(
                [
                    SimpleNamespace(
                        event_day_id="ed-20",
                        operational_phase_id=PHASE_TARDE,
                        start_min=1380,
                        end_min=1440,
                    )
                ]
            ),
            _scalars_result([SimpleNamespace(id=PHASE_TARDE, name="tarde")]),
        ]

        resp = client.get(ENDPOINT, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["buckets"][0]["phase"] == "tarde"

        days_sql, days_params = _compiled(db_mock, 2)
        assert "event_days.date IN" in days_sql
        flat = _flatten(days_params.values())
        assert date(2026, 7, 20) in flat
        assert date(2026, 7, 21) not in flat

    def test_bucket_local_de_0030_resuelve_contra_el_dia_21(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([SimpleNamespace(bucket=datetime(2026, 7, 21, 0, 30), count=4)]),
            _scalars_result(
                [SimpleNamespace(id="ed-21", date=date(2026, 7, 21))]
            ),
            _scalars_result(
                [
                    SimpleNamespace(
                        event_day_id="ed-21",
                        operational_phase_id=PHASE_TARDE,
                        start_min=0,
                        end_min=360,
                    )
                ]
            ),
            _scalars_result([SimpleNamespace(id=PHASE_TARDE, name="madrugada")]),
        ]

        resp = client.get(ENDPOINT, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["buckets"][0]["phase"] == "madrugada"

        _days_sql, days_params = _compiled(db_mock, 2)
        flat = _flatten(days_params.values())
        assert date(2026, 7, 21) in flat
        assert date(2026, 7, 20) not in flat

    def test_minuto_del_bucket_usa_hora_local(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        # 23:30 local => minuto 1410, dentro de la fase [1380, 1440).
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([SimpleNamespace(bucket=datetime(2026, 7, 20, 23, 30), count=1)]),
            _scalars_result(
                [SimpleNamespace(id="ed-20", date=date(2026, 7, 20))]
            ),
            _scalars_result(
                [
                    SimpleNamespace(
                        event_day_id="ed-20",
                        operational_phase_id=PHASE_TARDE,
                        start_min=1380,
                        end_min=1410,
                    )
                ]
            ),
            _scalars_result([SimpleNamespace(id=PHASE_TARDE, name="tarde")]),
        ]

        resp = client.get(ENDPOINT, headers=auth_headers)
        assert resp.status_code == 200
        # 1410 es el límite exclusivo: la fase no aplica y el bucket queda sin
        # fase (None), no con la etiqueta "unassigned".
        assert resp.json()["buckets"][0]["phase"] is None


class TestAbsoluteBoundsRequired:
    def test_400_si_start_naive(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            ENDPOINT,
            params={"start": "2026-07-21T00:00:00"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "absolute instants" in resp.json()["detail"]
        assert not db_mock.execute.await_args_list

    def test_400_si_end_naive(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            ENDPOINT,
            params={"end": "2026-07-21T23:59:59"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert not db_mock.execute.await_args_list

    def test_400_si_ambos_naive_reporta_ambos(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            ENDPOINT,
            params={"start": "2026-07-21T00:00:00", "end": "2026-07-21T23:59:59"},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "start" in detail
        assert "end" in detail

    @pytest.mark.parametrize(
        "value",
        [
            "2026-07-21T03:00:00Z",
            "2026-07-21T03:00:00+00:00",
            "2026-07-21T00:00:00-03:00",
        ],
    )
    def test_acepta_extremos_con_offset(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
        value: str,
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([]),
            _scalars_result([]),
        ]

        resp = client.get(
            ENDPOINT,
            params={"start": value, "granularity": "hour"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    def test_sin_periodo_sigue_operando_en_modo_evento(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.side_effect = [
            _event_result(_event(EVENT_START, EVENT_END)),
            _all_result([]),
        ]

        resp = client.get(ENDPOINT, params={"granularity": "day"}, headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["period"]["mode"] == "event"
