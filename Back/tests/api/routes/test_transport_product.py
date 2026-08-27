"""Tests for the refactored deterministic transport adapter and endpoint.

All DB access is mocked — only the adapter's logic and the route's HTTP contract
are tested.  PostGIS is NOT required.
"""
from __future__ import annotations

from datetime import datetime, timedelta, time, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.db.session import get_async_db
from app.main import app
from app.schemas.product import TransportRecommendationResponse, ZonaTransporteItem
from src.interfaces.rest.transport_product import (
    _haversine_distance_m,
    _resolve_day_type,
    get_transport_product_adapter,
)

EVENT_ID = "test-event-1"
BASE_URL = f"/api/events/{EVENT_ID}"

USER_LAT = -31.4201
USER_LNG = -64.1888


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(**kwargs) -> SimpleNamespace:
    defaults = dict(
        line_stop_id="ls-001",
        stop_order=1,
        line_id="line-001",
        line_name="Línea 1",
        company="CopSA",
        zone_id="zone-001",
        zone_name="Parada Centro",
        latitude=-31.42,
        longitude=-64.19,
        calle="Av. San Martín",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_schedule(**kwargs) -> SimpleNamespace:
    defaults = dict(
        id="sched-001",
        line_stop_id="ls-001",
        day_type="weekday",
        departure_time=time(8, 0),
        destination="Córdoba",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _mock_db(
    rows: list[SimpleNamespace],
    schedules: list | None = None,
    extra_results: list | None = None,
):
    """Create a mock AsyncSession.

    Call order depends on adapter logic:

    **Without destination** (2 calls):
        1. Main query → ``.all()`` returns *rows*
        2. Schedules → ``.scalars().all()`` returns *schedules*

    **With destination** (4 calls):
        1. Main query → ``.all()`` returns *rows*
        2. Destination lookup → ``.all()`` returns *extra_results[0]*
        3. Line-ID lookup → ``.all()`` returns *extra_results[1]*
        4. Schedules → ``.scalars().all()`` returns *schedules*
    """
    db = AsyncMock()

    main_result = MagicMock()
    main_result.all.return_value = rows

    sched_result = MagicMock()
    sched_result.scalars.return_value.all.return_value = schedules or []

    extra_objs = []
    if extra_results:
        for raw in extra_results:
            obj = MagicMock()
            obj.all.return_value = raw
            extra_objs.append(obj)

    call_count = 0

    async def execute_side_effect(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return main_result
        if extra_objs:
            idx = call_count - 2
            if idx < len(extra_objs):
                return extra_objs[idx]
        return sched_result

    db.execute = AsyncMock(side_effect=execute_side_effect)
    return db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Unit tests: helper functions
# ---------------------------------------------------------------------------

class TestHaversineDistance:
    def test_same_point_returns_zero(self):
        assert _haversine_distance_m(-31.42, -64.19, -31.42, -64.19) == 0.0

    def test_known_distance_approx(self):
        d = _haversine_distance_m(-31.420, -64.188, -31.429, -64.188)
        assert 900 < d < 1100


class TestResolveDayType:
    def test_weekday(self):
        assert _resolve_day_type(datetime(2026, 8, 24, 10, 0)) == "weekday"

    def test_saturday(self):
        assert _resolve_day_type(datetime(2026, 8, 29, 10, 0)) == "saturday"

    def test_sunday(self):
        assert _resolve_day_type(datetime(2026, 8, 30, 10, 0)) == "sunday_holiday"


# ---------------------------------------------------------------------------
# Unit tests: adapter logic
# ---------------------------------------------------------------------------

class TestTransportAdapter:
    @pytest.mark.asyncio
    async def test_200_ok_with_schedules(self):
        rows = [_make_row()]
        schedules = [_make_schedule(departure_time=time(10, 30))]
        db = _mock_db(rows, schedules)

        result = await get_transport_product_adapter(
            db=db,
            timestamp=datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc),
            event_id=EVENT_ID,
        )

        assert result.event_id == EVENT_ID
        assert result.mode == "informar"
        assert len(result.zonas) == 1
        zona = result.zonas[0]
        assert zona.line_name == "Línea 1"
        assert zona.company == "CopSA"
        # 2026-08-26 10:00 UTC == 07:00 local (UTC-3); 10:30 - 07:00 = 210 min
        assert zona.next_departure == "10:30"
        assert zona.minutes_until_next == 210
        assert zona.destination is None
        assert zona.is_tomorrow is False

    @pytest.mark.asyncio
    async def test_filters_by_destination(self):
        rows = [
            _make_row(line_stop_id="ls-001", line_id="line-001", line_name="Línea A"),
            _make_row(line_stop_id="ls-002", line_id="line-002", line_name="Línea B",
                      zone_id="zone-002", zone_name="Parada B"),
        ]
        schedules = [
            _make_schedule(line_stop_id="ls-001", destination="Córdoba"),
            _make_schedule(line_stop_id="ls-002", destination="Villa Carlos Paz"),
        ]
        # Call 2: sched_stmt → line_stop_ids matching destination
        # Call 3: ls_stmt → line_ids from those line_stop_ids
        extra = [
            [("ls-001",)],
            [("line-001",)],
        ]
        db = _mock_db(rows, schedules, extra_results=extra)

        result = await get_transport_product_adapter(
            db=db,
            timestamp=datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc),
            event_id=EVENT_ID,
            destination="Córdoba",
        )

        assert len(result.zonas) == 1
        assert result.zonas[0].line_name == "Línea A"
        assert result.zonas[0].destination == "Córdoba"

    @pytest.mark.asyncio
    async def test_is_nearest_marked(self):
        rows = [
            _make_row(zone_id="z-far", zone_name="Lejana",
                      latitude=-31.40, longitude=-64.20),
            _make_row(line_stop_id="ls-002", zone_id="z-near", zone_name="Cercana",
                      latitude=-31.42, longitude=-64.19, stop_order=2),
        ]
        schedules = [
            _make_schedule(line_stop_id="ls-001", departure_time=time(10, 0)),
            _make_schedule(line_stop_id="ls-002", departure_time=time(10, 15)),
        ]
        db = _mock_db(rows, schedules)

        result = await get_transport_product_adapter(
            db=db,
            timestamp=datetime(2026, 8, 26, 9, 0, tzinfo=timezone.utc),
            event_id=EVENT_ID,
            user_latitude=USER_LAT,
            user_longitude=USER_LNG,
        )

        assert len(result.zonas) == 2
        nearest = [z for z in result.zonas if z.is_nearest]
        assert len(nearest) == 1
        assert nearest[0].zone_id == "z-near"

    @pytest.mark.asyncio
    async def test_distance_ordering(self):
        rows = [
            _make_row(zone_id="z-far", zone_name="Lejana",
                      latitude=-31.40, longitude=-64.20),
            _make_row(line_stop_id="ls-002", zone_id="z-near", zone_name="Cercana",
                      latitude=-31.42, longitude=-64.19, stop_order=2),
        ]
        schedules = [
            _make_schedule(line_stop_id="ls-001"),
            _make_schedule(line_stop_id="ls-002", departure_time=time(10, 15)),
        ]
        db = _mock_db(rows, schedules)

        result = await get_transport_product_adapter(
            db=db,
            timestamp=datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc),
            event_id=EVENT_ID,
            user_latitude=USER_LAT,
            user_longitude=USER_LNG,
        )

        distances = [z.distancia_min for z in result.zonas]
        assert distances == sorted(distances, key=lambda d: d if d is not None else float("inf"))

    @pytest.mark.asyncio
    async def test_empty_when_no_lines(self):
        db = _mock_db([], [])

        result = await get_transport_product_adapter(
            db=db,
            timestamp=datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc),
            event_id=EVENT_ID,
        )

        assert result.mode == "sin_solucion"
        assert result.zonas == []

    @pytest.mark.asyncio
    async def test_empty_when_no_matching_destination(self):
        rows = [_make_row(line_name="Línea A")]
        schedules = []
        # Call 2: sched_stmt → no matching line_stop_ids
        extra = [[]]
        db = _mock_db(rows, schedules, extra_results=extra)

        result = await get_transport_product_adapter(
            db=db,
            timestamp=datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc),
            event_id=EVENT_ID,
            destination="Córdoba",
        )

        assert result.mode == "sin_solucion"
        assert result.zonas == []

    @pytest.mark.asyncio
    async def test_stops_without_coords_last(self):
        rows = [
            _make_row(zone_id="z-nocoord", zone_name="Sin Coord",
                      latitude=None, longitude=None),
            _make_row(line_stop_id="ls-002", zone_id="z-coord", zone_name="Con Coord",
                      latitude=-31.42, longitude=-64.19, stop_order=2),
        ]
        schedules = [
            _make_schedule(line_stop_id="ls-001", departure_time=time(10, 0)),
            _make_schedule(line_stop_id="ls-002", departure_time=time(10, 15)),
        ]
        db = _mock_db(rows, schedules)

        result = await get_transport_product_adapter(
            db=db,
            timestamp=datetime(2026, 8, 26, 9, 0, tzinfo=timezone.utc),
            event_id=EVENT_ID,
            user_latitude=USER_LAT,
            user_longitude=USER_LNG,
        )

        assert result.zonas[-1].zone_id == "z-nocoord"
        assert result.zonas[-1].is_nearest is False
        assert result.zonas[-1].distancia_min is None

    @pytest.mark.asyncio
    async def test_no_future_today_falls_back_to_tomorrow(self):
        rows = [_make_row()]
        schedules = [_make_schedule(departure_time=time(6, 0))]
        db = _mock_db(rows, schedules)

        result = await get_transport_product_adapter(
            db=db,
            timestamp=datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc),
            event_id=EVENT_ID,
        )

        zona = result.zonas[0]
        # 2026-08-26 10:00 UTC == 07:00 local. Today's 06:00 already passed; falls back to tomorrow 06:00
        assert zona.next_departure == "06:00"
        # 07:00 -> midnight = 1020 min; + 06:00 (360) = 1380
        assert zona.minutes_until_next == 1380
        assert zona.is_tomorrow is True
        assert zona.score == 1.0

    @pytest.mark.asyncio
    async def test_timezone_argentina_correct_minutes(self):
        """Regression: 17:11 local (== 20:11 UTC) vs a 21:10 local departure -> 239 min, not 59."""
        rows = [_make_row()]
        schedules = [_make_schedule(departure_time=time(21, 10))]
        db = _mock_db(rows, schedules)

        result = await get_transport_product_adapter(
            db=db,
            timestamp=datetime(2026, 8, 26, 20, 11, tzinfo=timezone.utc),  # 20:11 UTC == 17:11 local
            event_id=EVENT_ID,
        )

        zona = result.zonas[0]
        assert zona.next_departure == "21:10"
        assert zona.minutes_until_next == 239
        assert zona.is_tomorrow is False

    @pytest.mark.asyncio
    async def test_next_day_service(self):
        """23:30 local (21:00 -> service ended) -> first service next day at 06:20."""
        rows = [_make_row()]
        schedules = [
            _make_schedule(departure_time=time(6, 20)),
            _make_schedule(departure_time=time(23, 0)),
        ]
        db = _mock_db(rows, schedules)

        # 2026-08-27 02:30 UTC == 2026-08-26 23:30 local (Wednesday)
        result = await get_transport_product_adapter(
            db=db,
            timestamp=datetime(2026, 8, 27, 2, 30, tzinfo=timezone.utc),
            event_id=EVENT_ID,
        )

        zona = result.zonas[0]
        assert zona.next_departure == "06:20"
        # 23:30 -> midnight = 30 min; + 06:20 (380) = 410
        assert zona.minutes_until_next == 410
        assert zona.is_tomorrow is True

    @pytest.mark.asyncio
    async def test_limit_truncates_results(self):
        rows = [
            _make_row(zone_id=f"z-{i}", zone_name=f"Parada {i}",
                      latitude=-31.42 + i * 0.01, longitude=-64.19 + i * 0.01,
                      line_stop_id=f"ls-{i}", stop_order=i)
            for i in range(10)
        ]
        schedules = [
            _make_schedule(line_stop_id=f"ls-{i}", departure_time=time(10, i))
            for i in range(10)
        ]
        db = _mock_db(rows, schedules)

        result = await get_transport_product_adapter(
            db=db,
            timestamp=datetime(2026, 8, 26, 9, 0, tzinfo=timezone.utc),
            event_id=EVENT_ID,
            user_latitude=USER_LAT,
            user_longitude=USER_LNG,
            limit=3,
        )

        assert len(result.zonas) == 3


# ---------------------------------------------------------------------------
# Endpoint HTTP contract tests
# ---------------------------------------------------------------------------

class TestTransportEndpointHTTP:
    @pytest.fixture(autouse=True)
    def _mock_adapter(self):
        with patch(
            "app.api.routes.transport.get_transport_product_adapter",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = TransportRecommendationResponse(
                event_id=EVENT_ID,
                timestamp=datetime.now(timezone.utc).isoformat(),
                mode="informar",
                zonas=[
                    ZonaTransporteItem(
                        zone_id="z-001",
                        name="Parada Centro",
                        score=1.0,
                        reasoning=["Próximo servicio"],
                        saturation_level=None,
                        estado=None,
                        availability=None,
                        estimated_wait=15,
                        confidence=None,
                        active_restriction="OPEN",
                        operational_state="HAS_SERVICE",
                        lat=-31.42,
                        lng=-64.19,
                        referencia="Av. San Martín",
                        distancia_min=500,
                        is_nearest=True,
                        calle="Av. San Martín",
                        line_name="Línea 1",
                        company="CopSA",
                        next_departure="10:30",
                        minutes_until_next=30,
                        destination="Córdoba",
                    ),
                ],
            )
            yield mock

    def test_200_ok_with_new_params(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
    ):
        resp = client.get(
            f"{BASE_URL}/products/transport",
            params={
                "destination": "Córdoba",
                "latitude": -31.42,
                "longitude": -64.19,
            },
            headers=auth_headers,
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["event_id"] == EVENT_ID
        assert body["mode"] == "informar"
        assert len(body["zonas"]) == 1

        zona = body["zonas"][0]
        assert zona["line_name"] == "Línea 1"
        assert zona["company"] == "CopSA"
        assert zona["next_departure"] == "10:30"
        assert zona["minutes_until_next"] == 30
        assert zona["destination"] == "Córdoba"

    def test_adapter_receives_new_params(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
    ):
        client.get(
            f"{BASE_URL}/products/transport",
            params={
                "destination": "Córdoba",
                "latitude": -31.42,
                "longitude": -64.19,
                "limit": 10,
            },
            headers=auth_headers,
        )

        _mock_adapter.assert_awaited_once()
        kwargs = _mock_adapter.await_args[1]
        assert kwargs["destination"] == "Córdoba"
        assert kwargs["user_latitude"] == pytest.approx(-31.42)
        assert kwargs["user_longitude"] == pytest.approx(-64.19)
        assert kwargs["limit"] == 10

    def test_adapter_receives_transport_type(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
    ):
        client.get(
            f"{BASE_URL}/products/transport",
            params={"transport_type": "urbano"},
            headers=auth_headers,
        )

        _mock_adapter.assert_awaited_once()
        kwargs = _mock_adapter.await_args[1]
        assert kwargs["transport_type"] == "urbano"

    @pytest.mark.parametrize("tt", ["urbano", "interurbano"])
    def test_transport_type_valid_values(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        tt: str,
    ):
        resp = client.get(
            f"{BASE_URL}/products/transport",
            params={"transport_type": tt},
            headers=auth_headers,
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize("tt", ["URBANO", "urb", "nacional", "aereo"])
    def test_transport_type_invalid_values_422(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        tt: str,
    ):
        resp = client.get(
            f"{BASE_URL}/products/transport",
            params={"transport_type": tt},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_destinations_endpoint_public(self, client: TestClient, mock_async_db: AsyncMock):
        result = MagicMock()
        result.all.return_value = [("Córdoba",), ("Los Nogales",)]
        mock_async_db.execute = AsyncMock(return_value=result)
        resp = client.get(f"{BASE_URL}/transport/destinations")
        assert resp.status_code == 200
        assert resp.json()["destinations"] == ["Córdoba", "Los Nogales"]

    def test_destinations_endpoint_filters_by_type(self, client: TestClient, mock_async_db: AsyncMock):
        result = MagicMock()
        result.all.return_value = [("Córdoba",)]
        mock_async_db.execute = AsyncMock(return_value=result)
        resp = client.get(
            f"{BASE_URL}/transport/destinations",
            params={"transport_type": "urbano"},
        )
        assert resp.status_code == 200
        assert resp.json()["destinations"] == ["Córdoba"]

    def test_destinations_invalid_type_422(self, client: TestClient):
        resp = client.get(
            f"{BASE_URL}/transport/destinations",
            params={"transport_type": "nacional"},
        )
        assert resp.status_code == 422

    def test_coordinates_optional(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        _mock_adapter: AsyncMock,
    ):
        resp = client.get(
            f"{BASE_URL}/products/transport",
            params={},
            headers=auth_headers,
        )

        assert resp.status_code == 200
        kwargs = _mock_adapter.await_args[1]
        assert kwargs["user_latitude"] is None
        assert kwargs["user_longitude"] is None
        assert kwargs["destination"] is None

    @pytest.mark.parametrize(
        "params",
        [
            {"latitude": -91.0, "longitude": -64.0},
            {"latitude": 91.0, "longitude": -64.0},
            {"latitude": -31.0, "longitude": -181.0},
            {"latitude": -31.0, "longitude": 181.0},
        ],
    )
    def test_out_of_range_coordinates_422(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        params: dict,
    ):
        resp = client.get(
            f"{BASE_URL}/products/transport",
            params=params,
            headers=auth_headers,
        )
        assert resp.status_code == 422

    def test_public_endpoint_no_auth_required(self, client: TestClient):
        resp = client.get(
            f"{BASE_URL}/products/transport",
            params={},
        )
        assert resp.status_code == 200

    def test_response_structure(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
    ):
        resp = client.get(
            f"{BASE_URL}/products/transport",
            params={},
            headers=auth_headers,
        )
        body = resp.json()
        zona = body["zonas"][0]

        expected_fields = {
            "zone_id", "name", "score", "reasoning",
            "saturation_level", "estado", "availability",
            "estimated_wait", "confidence", "active_restriction",
            "operational_state", "calle", "lat", "lng", "referencia",
            "distancia_min", "is_nearest",
            "line_name", "company", "next_departure",
            "minutes_until_next", "destination", "is_tomorrow",
        }
        assert set(zona.keys()) == expected_fields
