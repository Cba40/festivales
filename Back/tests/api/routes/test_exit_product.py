# backend/tests/api/routes/test_exit_product.py
# S2 (Salir V1): GET /api/events/{event_id}/products/exit
#
# Fixture propio: schema temporal desechable + override de get_async_db.
# Stack 100% async (AsyncSession + httpx.AsyncClient) porque el endpoint
# y los helpers de setup usan AsyncSession.
# Sin tablas geometry => no depende del PostGIS del entorno local.

from datetime import datetime
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.session import get_async_db
from app.main import app
from app.models.exit_destination import ExitDestination
from app.models.exit_zone_destination import exit_zone_destinations_table

EVENT_ID = "663e6e32-9d4a-4f20-b992-3585b9310522"
OTHER_EVENT_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
NORTE_ID = "b8a6ff92-0fce-4a53-8262-20b0c2d05f0c"
SUR_ID = "4a2fbeef-b6d0-4530-8a5e-b192853f5d56"

SCRATCH_DDL = """
CREATE TABLE events (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255)
);
CREATE TABLE zones (
    id VARCHAR(36) PRIMARY KEY,
    event_id VARCHAR(36) REFERENCES events(id),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    status VARCHAR(20),
    transporte VARCHAR(50),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);
CREATE TABLE exit_destinations (
    id VARCHAR(36) PRIMARY KEY,
    event_id VARCHAR(36) NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT uq_exit_dest_event_name UNIQUE (event_id, name)
);
CREATE TABLE exit_zone_destinations (
    exit_zone_id VARCHAR(36) NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    destination_id VARCHAR(36) NOT NULL REFERENCES exit_destinations(id) ON DELETE CASCADE,
    PRIMARY KEY (exit_zone_id, destination_id)
);
"""


@pytest.fixture()
async def exit_env():
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    conn = await engine.connect()
    trans = await conn.begin()
    await conn.execute(text("DROP SCHEMA IF EXISTS tmp_exit_api CASCADE"))
    await conn.execute(text("CREATE SCHEMA tmp_exit_api"))
    await conn.execute(text("SET LOCAL search_path TO tmp_exit_api"))
    await conn.exec_driver_sql(SCRATCH_DDL)
    await conn.execute(
        text("INSERT INTO events (id, name) VALUES (:id, :name)"),
        {"id": EVENT_ID, "name": "Festival de Jesús María 2026"},
    )

    session_maker = async_sessionmaker(bind=conn, expire_on_commit=False)
    session = session_maker()

    async def _override_get_async_db():
        yield session

    app.dependency_overrides[get_async_db] = _override_get_async_db
    # ASGITransport no ejecuta lifespan: ideal para tests unitarios de ruta.
    client = httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )
    try:
        yield SimpleNamespace(client=client, session=session)
    finally:
        await client.aclose()
        app.dependency_overrides.clear()
        await session.close()
        await trans.rollback()
        await conn.close()
        await engine.dispose()


async def _crear_zona(session, zone_id, event_id, name, ztype="salida", status="activa",
                      transporte=None, lat=None, lng=None):
    await session.execute(
        text(
            "INSERT INTO zones (id, event_id, name, type, status, transporte, latitude, longitude) "
            "VALUES (:id, :event_id, :name, :type, :status, :transporte, :lat, :lng)"
        ),
        {"id": zone_id, "event_id": event_id, "name": name, "type": ztype,
         "status": status, "transporte": transporte, "lat": lat, "lng": lng},
    )


async def _crear_destino(session, name, event_id=EVENT_ID, active=True):
    destino = ExitDestination(event_id=event_id, name=name, active=active)
    session.add(destino)
    await session.flush()
    return destino


async def _relacionar(session, zone_id, destino):
    await session.execute(
        exit_zone_destinations_table.insert().values(
            exit_zone_id=zone_id, destination_id=destino.id
        )
    )
    await session.flush()


async def _salidas_base(session):
    await _crear_zona(session, NORTE_ID, EVENT_ID, "Salida Norte Auto",
                      transporte="vehicular", lat=-30.978013371272713, lng=-64.08494797229652)
    await _crear_zona(session, SUR_ID, EVENT_ID, "Salida Sur Peatonal",
                      transporte="peatonal", lat=-30.985337, lng=-64.094209)
    cordoba = await _crear_destino(session, "Córdoba")
    caroya = await _crear_destino(session, "Colonia Caroya")
    sinsacate = await _crear_destino(session, "Sinsacate")
    sierras = await _crear_destino(session, "Sierras Chicas")
    for dest in (cordoba, caroya, sinsacate):
        await _relacionar(session, NORTE_ID, dest)
    await _relacionar(session, SUR_ID, sierras)
    return {"cordoba": cordoba.id, "caroya": caroya.id,
            "sinsacate": sinsacate.id, "sierras": sierras.id}


class TestExitProductEndpoint:

    async def test_200_ok(self, exit_env) -> None:
        await _salidas_base(exit_env.session)

        response = await exit_env.client.get(f"/api/events/{EVENT_ID}/products/exit")

        assert response.status_code == 200
        body = response.json()
        assert body["event_id"] == EVENT_ID
        assert len(body["zonas"]) == 2

        por_nombre = {z["name"]: z for z in body["zonas"]}
        norte = por_nombre["Salida Norte Auto"]
        assert norte["transporte"] == "vehicular"
        assert norte["status"] == "activa"
        assert norte["lat"] == pytest.approx(-30.978013371272713)
        assert [d["name"] for d in norte["destinations"]] == [
            "Colonia Caroya", "Córdoba", "Sinsacate",  # orden Unicode: 'l' < 'ó'
        ]

        sur = por_nombre["Salida Sur Peatonal"]
        assert sur["transporte"] == "peatonal"
        assert [d["name"] for d in sur["destinations"]] == ["Sierras Chicas"]

    async def test_empty_when_no_salidas(self, exit_env) -> None:
        await _crear_destino(exit_env.session, "Córdoba")

        response = await exit_env.client.get(f"/api/events/{EVENT_ID}/products/exit")

        assert response.status_code == 200
        assert response.json()["zonas"] == []

    async def test_empty_when_no_destinations(self, exit_env) -> None:
        await _crear_zona(exit_env.session, NORTE_ID, EVENT_ID,
                          "Salida Norte Auto", transporte="vehicular")

        response = await exit_env.client.get(f"/api/events/{EVENT_ID}/products/exit")

        assert response.status_code == 200
        zonas = response.json()["zonas"]
        assert len(zonas) == 1
        assert zonas[0]["destinations"] == []

    async def test_filters_by_event_id(self, exit_env) -> None:
        env = exit_env
        await env.session.execute(
            text("INSERT INTO events (id, name) VALUES (:id, :name)"),
            {"id": OTHER_EVENT_ID, "name": "Otro Evento"},
        )
        await _crear_zona(env.session, NORTE_ID, EVENT_ID,
                          "Salida Norte Auto", transporte="vehicular")
        await _crear_zona(env.session, "cccccccc-1111-2222-3333-444444444444",
                          OTHER_EVENT_ID, "Salida De Otro Evento", transporte="vehicular")
        await _crear_destino(env.session, "Destino Otro Evento", event_id=OTHER_EVENT_ID)

        response = await env.client.get(f"/api/events/{EVENT_ID}/products/exit")

        assert response.status_code == 200
        zonas = response.json()["zonas"]
        assert [z["zone_id"] for z in zonas] == [NORTE_ID]
        assert all(
            d["name"] != "Destino Otro Evento"
            for z in zonas for d in z["destinations"]
        )

    async def test_excludes_inactive_destinations(self, exit_env) -> None:
        env = exit_env
        await _crear_zona(env.session, NORTE_ID, EVENT_ID,
                          "Salida Norte Auto", transporte="vehicular")
        activo = await _crear_destino(env.session, "Córdoba", active=True)
        inactivo = await _crear_destino(env.session, "Destino Desactivado", active=False)
        await _relacionar(env.session, NORTE_ID, activo)
        await _relacionar(env.session, NORTE_ID, inactivo)

        response = await env.client.get(f"/api/events/{EVENT_ID}/products/exit")

        assert response.status_code == 200
        destinations = response.json()["zonas"][0]["destinations"]
        assert [d["name"] for d in destinations] == ["Córdoba"]

    async def test_excludes_closed_zones(self, exit_env) -> None:
        env = exit_env
        await _crear_zona(env.session, NORTE_ID, EVENT_ID,
                          "Salida Norte Auto", transporte="vehicular")
        await _crear_zona(env.session, SUR_ID, EVENT_ID,
                          "Salida Cerrada", status="cerrada")

        response = await env.client.get(f"/api/events/{EVENT_ID}/products/exit")

        assert response.status_code == 200
        zonas = response.json()["zonas"]
        assert [z["name"] for z in zonas] == ["Salida Norte Auto"]

    async def test_response_structure(self, exit_env) -> None:
        await _salidas_base(exit_env.session)

        response = await exit_env.client.get(f"/api/events/{EVENT_ID}/products/exit")

        assert response.status_code == 200
        body = response.json()
        assert set(body.keys()) == {"event_id", "timestamp", "zonas"}
        datetime.fromisoformat(body["timestamp"])  # ISO-8601 parseable

        zona = body["zonas"][0]
        assert set(zona.keys()) == {
            "zone_id", "name", "transporte", "lat", "lng", "status", "is_nearest", "destinations",
        }
        assert zona["is_nearest"] is False  # sin GPS nadie es marcada
        for destino in zona["destinations"]:
            assert set(destino.keys()) == {"id", "name", "active"}
            assert isinstance(destino["active"], bool)


class TestExitProductFilters:

    async def test_filters_by_mode(self, exit_env) -> None:
        await _salidas_base(exit_env.session)
        env = exit_env

        response_vehicular = await env.client.get(
            f"/api/events/{EVENT_ID}/products/exit", params={"mode": "vehicular"}
        )
        response_peatonal = await env.client.get(
            f"/api/events/{EVENT_ID}/products/exit", params={"mode": "peatonal"}
        )
        response_transporte = await env.client.get(
            f"/api/events/{EVENT_ID}/products/exit", params={"mode": "transporte"}
        )

        assert response_vehicular.status_code == 200
        zonas_v = response_vehicular.json()["zonas"]
        assert [z["transporte"] for z in zonas_v] == ["vehicular"]
        assert zonas_v[0]["zone_id"] == NORTE_ID

        assert [z["zone_id"] for z in response_peatonal.json()["zonas"]] == [SUR_ID]
        assert response_transporte.json()["zonas"] == []

    async def test_mode_invalido_rechazado(self, exit_env) -> None:
        response = await exit_env.client.get(
            f"/api/events/{EVENT_ID}/products/exit", params={"mode": "auto"}
        )
        assert response.status_code == 422

    async def test_filters_by_destination(self, exit_env) -> None:
        destinos = await _salidas_base(exit_env.session)
        env = exit_env

        response = await env.client.get(
            f"/api/events/{EVENT_ID}/products/exit",
            params={"destination_id": destinos["cordoba"]},
        )
        response_sin_relacion = await env.client.get(
            f"/api/events/{EVENT_ID}/products/exit",
            params={"destination_id": SUR_ID},  # un id de zona no es destino
        )

        assert response.status_code == 200
        zonas = response.json()["zonas"]
        # El filtro restringe QUÉ ZONAS aparecen; los destinos de cada
        # zona se listan completos.
        assert [z["zone_id"] for z in zonas] == [NORTE_ID]
        assert [d["name"] for d in zonas[0]["destinations"]] == [
            "Colonia Caroya", "Córdoba", "Sinsacate",
        ]

        assert response_sin_relacion.status_code == 200
        assert response_sin_relacion.json()["zonas"] == []

    async def test_is_nearest_marked(self, exit_env) -> None:
        await _salidas_base(exit_env.session)
        # Punto claramente más cerca de la Salida Sur que de la Norte
        response = await exit_env.client.get(
            f"/api/events/{EVENT_ID}/products/exit",
            params={"latitude": -30.9850, "longitude": -64.0938},
        )

        assert response.status_code == 200
        zonas = response.json()["zonas"]
        flags = {z["name"]: z["is_nearest"] for z in zonas}
        assert flags["Salida Sur Peatonal"] is True
        assert flags["Salida Norte Auto"] is False
        assert sum(flags.values()) == 1

    async def test_distance_ordering(self, exit_env) -> None:
        await _salidas_base(exit_env.session)
        # Tercera salida sin coordenadas: debe quedar siempre última
        await _crear_zona(exit_env.session, "dddddddd-1111-2222-3333-444444444444",
                          EVENT_ID, "Salida Sin Coordenadas", transporte="vehicular")
        client = exit_env.client

        cerca_norte = await client.get(
            f"/api/events/{EVENT_ID}/products/exit",
            params={"latitude": -30.9785, "longitude": -64.0852},
        )
        cerca_sur = await client.get(
            f"/api/events/{EVENT_ID}/products/exit",
            params={"latitude": -30.9850, "longitude": -64.0938},
        )
        sin_gps = await client.get(f"/api/events/{EVENT_ID}/products/exit")

        nombres_norte = [z["name"] for z in cerca_norte.json()["zonas"]]
        nombres_sur = [z["name"] for z in cerca_sur.json()["zonas"]]
        # Orden por distancia ascendente; la sin coords al final
        assert nombres_norte == ["Salida Norte Auto", "Salida Sur Peatonal",
                                 "Salida Sin Coordenadas"]
        assert nombres_sur == ["Salida Sur Peatonal", "Salida Norte Auto",
                               "Salida Sin Coordenadas"]
        # is_nearest solo sobre la primera con coordenadas reales
        assert cerca_norte.json()["zonas"][0]["is_nearest"] is True
        assert cerca_norte.json()["zonas"][-1]["is_nearest"] is False

        # Sin GPS se conserva el orden alfabético estable
        assert [z["name"] for z in sin_gps.json()["zonas"]] == sorted(nombres_norte)
