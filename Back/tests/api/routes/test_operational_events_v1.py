# backend/tests/api/routes/test_operational_events_v1.py
# RFC-OPERATIONAL-EVENTS-V1 / Fase 2 — CRUD endpoints de OperationalEvent.
#
# Stack 100% async (AsyncSession + httpx.AsyncClient). Cada test usa un
# schema temporal desechable (tmp_oe_api) con solo las tablas necesarias
# (event_days, zones, operational_events V1), sin geometry => no depende
# del PostGIS del entorno local. El search_path se fija a nivel de conexion
# (SET, no SET LOCAL) para que sobreviva a los commits del CRUD.

import httpx
import pytest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from jose import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.session import get_async_db
from app.main import app

ED_ID = "ed-fase2"
ZONE_ID = "zone-fase2"
RANDOM_UUID = "00000000-0000-0000-0000-000000000000"

FUTURE_START = "2027-01-15T20:00:00+00:00"
FUTURE_END = "2027-01-15T22:00:00+00:00"
PAST_START = "2026-01-10T20:00:00+00:00"
PAST_END = "2026-01-10T22:00:00+00:00"

SCRATCH_DDL = """
CREATE TABLE event_days (
    id VARCHAR(36) PRIMARY KEY
);
CREATE TABLE zones (
    id VARCHAR(36) PRIMARY KEY
);
CREATE TABLE operational_events (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    event_day_id VARCHAR(36) NOT NULL REFERENCES event_days(id) ON DELETE CASCADE,
    zone_id VARCHAR(36) NOT NULL REFERENCES zones(id),
    event_type VARCHAR(50) NOT NULL,
    description TEXT,
    effect_type VARCHAR(30) NOT NULL,
    effect_value INTEGER,
    is_incident BOOLEAN NOT NULL DEFAULT false,
    start_timestamp TIMESTAMPTZ NOT NULL,
    end_timestamp TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    latitude NUMERIC(10,8),
    longitude NUMERIC(11,8),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_operational_events_temporal CHECK (end_timestamp > start_timestamp),
    CONSTRAINT ck_operational_events_latitude CHECK (latitude IS NULL OR (latitude BETWEEN -90 AND 90)),
    CONSTRAINT ck_operational_events_longitude CHECK (longitude IS NULL OR (longitude BETWEEN -180 AND 180)),
    CONSTRAINT ck_operational_events_effect_value CHECK (
        (effect_type = 'reduccion_capacidad' AND effect_value IS NOT NULL AND effect_value BETWEEN 1 AND 100) OR
        (effect_type = 'cierre_total' AND effect_value IS NULL) OR
        (effect_type = 'aumento_demanda' AND effect_value IS NOT NULL AND effect_value >= 1) OR
        (effect_type = 'incidente_sin_impacto' AND effect_value IS NULL)
    )
);
CREATE TABLE predictions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL UNIQUE
);
"""


@pytest.fixture()
async def oe_env():
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    conn = await engine.connect()
    await conn.execute(text("DROP SCHEMA IF EXISTS tmp_oe_api CASCADE"))
    await conn.execute(text("CREATE SCHEMA tmp_oe_api"))
    await conn.execute(text("SET search_path TO tmp_oe_api, public"))
    await conn.exec_driver_sql(SCRATCH_DDL)
    await conn.execute(text("INSERT INTO event_days (id) VALUES (:id)"), {"id": ED_ID})
    await conn.execute(text("INSERT INTO zones (id) VALUES (:id)"), {"id": ZONE_ID})

    session = async_sessionmaker(bind=conn, expire_on_commit=False)()

    async def _override_get_async_db():
        yield session

    app.dependency_overrides[get_async_db] = _override_get_async_db
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )
    try:
        yield SimpleNamespace(client=client, session=session)
    finally:
        await client.aclose()
        app.dependency_overrides.clear()
        await session.close()
        await conn.close()
        await engine.dispose()


def _auth_headers() -> dict:
    expire = datetime.now(timezone.utc) + timedelta(hours=8)
    token = jwt.encode(
        {"sub": "admin", "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def _valid_body(overrides: dict | None = None) -> dict:
    body = {
        "event_day_id": ED_ID,
        "zone_id": ZONE_ID,
        "event_type": "accidente",
        "description": "Evento Fase 2",
        "effect_type": "reduccion_capacidad",
        "effect_value": 50,
        "is_incident": True,
        "start_timestamp": FUTURE_START,
        "end_timestamp": FUTURE_END,
    }
    if overrides:
        body.update(overrides)
    return body


async def _crear(env, overrides=None) -> dict:
    response = await env.client.post(
        "/api/operational-events/",
        json=_valid_body(overrides),
        headers=_auth_headers(),
    )
    assert response.status_code == 201
    return response.json()


async def _marcar_usado_por_motor(env, timestamp: str) -> None:
    await env.session.execute(
        text("INSERT INTO predictions (timestamp) VALUES (:ts)"),
        {"ts": timestamp},
    )
    await env.session.commit()


class TestAuthentication:

    async def test_401_no_auth(self, oe_env) -> None:
        response = await oe_env.client.post(
            "/api/operational-events/", json=_valid_body()
        )
        assert response.status_code == 401


class TestCreate:

    async def test_create_reduccion_capacidad(self, oe_env) -> None:
        body = await _crear(oe_env)
        assert body["effect_type"] == "reduccion_capacidad"
        assert body["effect_value"] == 50
        assert body["event_day_id"] == ED_ID
        assert body["is_active"] is True
        assert body["id"]

    async def test_create_cierre_total(self, oe_env) -> None:
        body = await _crear(oe_env, {"effect_type": "cierre_total", "effect_value": None})
        assert body["effect_type"] == "cierre_total"
        assert body["effect_value"] is None

    async def test_create_aumento_demanda(self, oe_env) -> None:
        body = await _crear(oe_env, {"effect_type": "aumento_demanda", "effect_value": 200})
        assert body["effect_type"] == "aumento_demanda"
        assert body["effect_value"] == 200

    async def test_create_incidente_sin_impacto(self, oe_env) -> None:
        body = await _crear(oe_env, {"effect_type": "incidente_sin_impacto", "effect_value": None})
        assert body["effect_type"] == "incidente_sin_impacto"
        assert body["effect_value"] is None

    async def test_create_incidente_operativo_forces_is_incident_true(self, oe_env) -> None:
        body = await _crear(oe_env, {
            "event_type": "incidente_operativo",
            "effect_type": "incidente_sin_impacto",
            "effect_value": None,
            "is_incident": False,
        })
        assert body["event_type"] == "incidente_operativo"
        assert body["is_incident"] is True

    async def test_create_other_type_respects_is_incident_false(self, oe_env) -> None:
        body = await _crear(oe_env, {
            "event_type": "accidente",
            "effect_type": "incidente_sin_impacto",
            "effect_value": None,
            "is_incident": False,
        })
        assert body["event_type"] == "accidente"
        assert body["is_incident"] is False

    async def test_create_with_coordinates(self, oe_env) -> None:
        body = await _crear(oe_env, {
            "latitude": -31.4201,
            "longitude": -64.1888,
        })
        assert body["latitude"] == -31.4201
        assert body["longitude"] == -64.1888

    async def test_create_rejects_invalid_latitude(self, oe_env) -> None:
        response = await oe_env.client.post(
            "/api/operational-events/",
            json=_valid_body({"latitude": 91.0}),
            headers=_auth_headers(),
        )
        assert response.status_code == 422

    async def test_create_rejects_invalid_longitude(self, oe_env) -> None:
        response = await oe_env.client.post(
            "/api/operational-events/",
            json=_valid_body({"longitude": -181.0}),
            headers=_auth_headers(),
        )
        assert response.status_code == 422

    async def test_create_rejects_invalid_effect_value(self, oe_env) -> None:
        response = await oe_env.client.post(
            "/api/operational-events/",
            json=_valid_body({"effect_value": 0}),
            headers=_auth_headers(),
        )
        assert response.status_code == 422

    async def test_create_rejects_end_before_start(self, oe_env) -> None:
        response = await oe_env.client.post(
            "/api/operational-events/",
            json=_valid_body({
                "start_timestamp": FUTURE_END,
                "end_timestamp": FUTURE_START,
            }),
            headers=_auth_headers(),
        )
        assert response.status_code == 422

    async def test_create_rejects_unknown_event_type(self, oe_env) -> None:
        response = await oe_env.client.post(
            "/api/operational-events/",
            json=_valid_body({"event_type": "terremoto"}),
            headers=_auth_headers(),
        )
        assert response.status_code == 422


class TestRead:

    async def test_get_by_id(self, oe_env) -> None:
        creado = await _crear(oe_env)
        response = await oe_env.client.get(
            f"/api/operational-events/{creado['id']}", headers=_auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["id"] == creado["id"]
        assert response.json()["description"] == "Evento Fase 2"

    async def test_get_by_id_not_found(self, oe_env) -> None:
        response = await oe_env.client.get(
            f"/api/operational-events/{RANDOM_UUID}", headers=_auth_headers(),
        )
        assert response.status_code == 404

    async def test_list_by_event_day(self, oe_env) -> None:
        await _crear(oe_env, {"description": "Evento A"})
        await _crear(oe_env, {"description": "Evento B"})
        response = await oe_env.client.get(
            f"/api/operational-events/by-event-day/{ED_ID}", headers=_auth_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 2
        assert {e["description"] for e in body} == {"Evento A", "Evento B"}


class TestUpdate:

    async def test_update_valid(self, oe_env) -> None:
        creado = await _crear(oe_env)
        response = await oe_env.client.put(
            f"/api/operational-events/{creado['id']}",
            json={"description": "Descripción nueva"},
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["description"] == "Descripción nueva"

    async def test_update_to_incidente_operativo_forces_is_incident_true(self, oe_env) -> None:
        creado = await _crear(oe_env, {
            "event_type": "tormenta",
            "effect_type": "incidente_sin_impacto",
            "effect_value": None,
            "is_incident": False,
        })
        assert creado["is_incident"] is False
        response = await oe_env.client.put(
            f"/api/operational-events/{creado['id']}",
            json={
                "event_type": "incidente_operativo",
                "effect_type": "incidente_sin_impacto",
                "effect_value": None,
            },
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        assert response.json()["event_type"] == "incidente_operativo"
        assert response.json()["is_incident"] is True

    async def test_update_rejects_expired_event(self, oe_env) -> None:
        creado = await _crear(oe_env, {
            "start_timestamp": PAST_START,
            "end_timestamp": PAST_END,
        })
        response = await oe_env.client.put(
            f"/api/operational-events/{creado['id']}",
            json={"description": "No debe aplicar"},
            headers=_auth_headers(),
        )
        assert response.status_code == 400

    async def test_update_rejects_invalid_timestamps(self, oe_env) -> None:
        creado = await _crear(oe_env)
        response = await oe_env.client.put(
            f"/api/operational-events/{creado['id']}",
            json={"start_timestamp": FUTURE_END, "end_timestamp": FUTURE_START},
            headers=_auth_headers(),
        )
        assert response.status_code == 422


class TestDeactivate:

    async def test_deactivate(self, oe_env) -> None:
        creado = await _crear(oe_env)
        response = await oe_env.client.patch(
            f"/api/operational-events/{creado['id']}/deactivate",
            headers=_auth_headers(),
        )
        assert response.status_code == 204

        verificado = await oe_env.client.get(
            f"/api/operational-events/{creado['id']}", headers=_auth_headers(),
        )
        assert verificado.status_code == 200
        assert verificado.json()["is_active"] is False

    async def test_deactivate_expired_event_succeeds(self, oe_env) -> None:
        creado = await _crear(oe_env, {
            "start_timestamp": PAST_START,
            "end_timestamp": PAST_END,
        })
        response = await oe_env.client.patch(
            f"/api/operational-events/{creado['id']}/deactivate",
            headers=_auth_headers(),
        )
        assert response.status_code == 204
        verificado = await oe_env.client.get(
            f"/api/operational-events/{creado['id']}", headers=_auth_headers(),
        )
        assert verificado.status_code == 200
        assert verificado.json()["is_active"] is False


class TestDelete:

    async def test_delete_valid(self, oe_env) -> None:
        creado = await _crear(oe_env)
        response = await oe_env.client.delete(
            f"/api/operational-events/{creado['id']}", headers=_auth_headers(),
        )
        assert response.status_code == 204

        verificado = await oe_env.client.get(
            f"/api/operational-events/{creado['id']}", headers=_auth_headers(),
        )
        assert verificado.status_code == 404

    async def test_delete_rejects_expired_event(self, oe_env) -> None:
        creado = await _crear(oe_env, {
            "start_timestamp": PAST_START,
            "end_timestamp": PAST_END,
        })
        response = await oe_env.client.delete(
            f"/api/operational-events/{creado['id']}", headers=_auth_headers(),
        )
        assert response.status_code == 400

    async def test_delete_rejects_event_used_by_engine(self, oe_env) -> None:
        creado = await _crear(oe_env)
        await _marcar_usado_por_motor(oe_env, "2027-01-15T21:00:00+00:00")
        response = await oe_env.client.delete(
            f"/api/operational-events/{creado['id']}", headers=_auth_headers(),
        )
        assert response.status_code == 409