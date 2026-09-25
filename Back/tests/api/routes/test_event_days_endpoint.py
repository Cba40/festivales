"""Tests HTTP del listado de jornadas operativas.

El endpoint ``GET /api/events/{event_id}/event-days`` ya existía; estos tests
fijan el contrato que necesita el selector de período de los informes:
autenticación, filtrado por ``event_id`` y orden por ``date`` ascendente.
No usa base de datos: se simula ``get_async_db`` con ``AsyncMock`` sobre el
CRUD real (``app.crud.event_day.list_by_event``).
"""

from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.db.session import get_async_db
from app.main import app

EVENT_ID = "11111111-1111-1111-1111-111111111111"
OTHER_EVENT_ID = "22222222-2222-2222-2222-222222222222"
ENDPOINT = "/api/events/{}/event-days"


def _day(day_id: str, day: date, day_of_week: str = "lun", is_active: bool = True):
    return SimpleNamespace(
        id=day_id,
        event_id=EVENT_ID,
        date=day,
        day_of_week=day_of_week,
        weather=None,
        headliner_artist=None,
        is_active=is_active,
        operational_profile_id=None,
        operational_start_min=1080,
        operational_end_min=120,
    )


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


class TestListEventDays:
    def test_401_without_token(self, client: TestClient, db_mock: AsyncMock):
        resp = client.get(ENDPOINT.format(EVENT_ID))
        assert resp.status_code == 401
        assert not db_mock.execute.await_args_list

    def test_devuelve_jornadas_en_orden_por_date(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        rows = [
            _day("ed-1", date(2026, 7, 15), "mié"),
            _day("ed-2", date(2026, 7, 16), "jue"),
            _day("ed-3", date(2026, 7, 17), "vie"),
        ]
        db_mock.execute.return_value = _scalars_result(rows)

        with patch(
            "app.api.routes.event_days.list_by_event", new=AsyncMock(return_value=rows)
        ) as list_mock:
            resp = client.get(
                ENDPOINT.format(EVENT_ID), headers=auth_headers
            )

        assert resp.status_code == 200
        body = resp.json()
        assert [d["id"] for d in body] == ["ed-1", "ed-2", "ed-3"]
        assert [d["date"] for d in body] == ["2026-07-15", "2026-07-16", "2026-07-17"]
        assert body[0]["day_of_week"] == "mié"
        assert body[0]["is_active"] is True
        list_mock.assert_awaited_once()
        assert list_mock.await_args.args[1] == EVENT_ID

    def test_filtra_por_event_id(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        rows = [_day("ed-1", date(2026, 7, 15))]
        list_mock = AsyncMock(return_value=rows)
        with patch("app.api.routes.event_days.list_by_event", new=list_mock):
            resp = client.get(
                ENDPOINT.format(OTHER_EVENT_ID), headers=auth_headers
            )

        assert resp.status_code == 200
        assert [d["id"] for d in resp.json()] == ["ed-1"]
        assert list_mock.await_args.args[1] == OTHER_EVENT_ID

    def test_consulta_ordena_por_date_y_filtra_por_event_id(
        self,
        client: TestClient,
        db_mock: AsyncMock,
        auth_headers: dict[str, str],
    ):
        db_mock.execute.return_value = _scalars_result([_day("ed-1", date(2026, 7, 15))])

        resp = client.get(ENDPOINT.format(EVENT_ID), headers=auth_headers)

        assert resp.status_code == 200
        assert [d["id"] for d in resp.json()] == ["ed-1"]
        sql = str(db_mock.execute.await_args_list[0].args[0].compile())
        assert "ORDER BY event_days.date" in sql
        assert "event_days.event_id" in sql

    def test_filtra_por_active_cuando_se_solicita(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        rows = [
            _day("ed-1", date(2026, 7, 15), is_active=True),
            _day("ed-2", date(2026, 7, 16), is_active=False),
        ]
        with patch(
            "app.api.routes.event_days.list_by_event", new=AsyncMock(return_value=rows)
        ):
            resp = client.get(
                ENDPOINT.format(EVENT_ID),
                params={"active": "true"},
                headers=auth_headers,
            )

        assert resp.status_code == 200
        assert [d["id"] for d in resp.json()] == ["ed-1"]

    def test_lista_vacia_devuelve_array(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        with patch(
            "app.api.routes.event_days.list_by_event", new=AsyncMock(return_value=[])
        ):
            resp = client.get(ENDPOINT.format(EVENT_ID), headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json() == []
