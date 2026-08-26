# backend/tests/api/routes/test_exit_admin.py
# Tests de gestión de destinos de salida (Dashboard > Infraestructura).
# Endpoints cubiertos:
#   GET/POST /api/events/{event_id}/exit-destinations
#   PUT/DELETE /api/events/{event_id}/exit-destinations/{id}
#   GET/PUT /api/events/{event_id}/zones/{zone_id}/exit-destinations
#
# Fixture propio: esquema temporal desechable sin tablas geometry => no
# depende del PostGIS del entorno local (misma estrategia que
# test_exit_product.py, pero con stack síncrono como los endpoints).

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.main import app
from app.models.exit_destination import ExitDestination
from app.models.exit_zone_destination import exit_zone_destinations_table

EVENT_ID = "event-exit-admin-a"
OTHER_EVENT_ID = "event-exit-admin-b"
ZONE_ID = "zone-salida-norte"
OTHER_ZONE_ID = "zone-salida-sur"

BASE = f"/api/events/{EVENT_ID}"

SCRATCH_DDL = """
CREATE TABLE events (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);
CREATE TABLE zones (
    id VARCHAR(36) PRIMARY KEY,
    event_id VARCHAR(36) NOT NULL REFERENCES events(id),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    saturation VARCHAR(20) NOT NULL DEFAULT 'bajo',
    status VARCHAR(20) NOT NULL DEFAULT 'activa',
    capacity INTEGER NOT NULL DEFAULT 0,
    available_capacity INTEGER NOT NULL DEFAULT 0,
    geometry_type VARCHAR(10)
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
def env():
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    connection = engine.connect()
    transaction = connection.begin()
    connection.exec_driver_sql("DROP SCHEMA IF EXISTS tmp_exit_admin CASCADE")
    connection.exec_driver_sql("CREATE SCHEMA tmp_exit_admin")
    connection.execute(text("SET LOCAL search_path TO tmp_exit_admin"))
    connection.exec_driver_sql(SCRATCH_DDL)

    session = Session(bind=connection, join_transaction_mode="create_savepoint")

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield SimpleNamespace(client=client, session=session)
    app.dependency_overrides.clear()
    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture()
def auth_headers() -> dict:
    expire = datetime.now(timezone.utc) + timedelta(hours=8)
    token = jwt.encode(
        {"sub": "admin", "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


def _crear_evento(session: Session, event_id: str = EVENT_ID) -> None:
    session.execute(
        text("INSERT INTO events (id, name) VALUES (:id, :name)"),
        {"id": event_id, "name": f"Evento {event_id}"},
    )
    session.flush()


def _crear_salida(
    session: Session,
    zone_id: str = ZONE_ID,
    event_id: str = EVENT_ID,
    name: str = "Salida Norte",
) -> None:
    session.execute(
        text(
            "INSERT INTO zones (id, event_id, name, type, saturation, status, "
            "capacity, available_capacity, geometry_type) "
            "VALUES (:id, :event_id, :name, 'salida', 'bajo', 'activa', 100, 100, 'point')"
        ),
        {"id": zone_id, "event_id": event_id, "name": name},
    )
    session.flush()


def _crear_destino(
    session: Session, name: str, event_id: str = EVENT_ID, active: bool = True
) -> ExitDestination:
    destino = ExitDestination(event_id=event_id, name=name, active=active)
    session.add(destino)
    session.flush()
    return destino


def _relacionar(session: Session, zone_id: str, destination_id: str) -> None:
    session.execute(
        exit_zone_destinations_table.insert().values(
            exit_zone_id=zone_id, destination_id=destination_id
        )
    )
    session.flush()


def _destinos_de_zona(env, zone_id: str) -> list[str]:
    rows = env.session.execute(
        select(exit_zone_destinations_table.c.destination_id).where(
            exit_zone_destinations_table.c.exit_zone_id == zone_id
        )
    ).scalars().all()
    return sorted(rows)


class TestListExitDestinations:

    def test_empty_list(self, env, auth_headers):
        _crear_evento(env.session)

        response = env.client.get(f"{BASE}/exit-destinations")

        assert response.status_code == 200
        assert response.json() == []

    def test_lists_created_destinations_ordered_by_name(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_destino(env.session, "Sinsacate")
        _crear_destino(env.session, "Colonia Caroya")
        _crear_destino(env.session, "Córdoba")

        response = env.client.get(f"{BASE}/exit-destinations")

        assert response.status_code == 200
        body = response.json()
        assert [d["name"] for d in body] == ["Colonia Caroya", "Córdoba", "Sinsacate"]
        for item in body:
            assert set(item.keys()) == {"id", "event_id", "name", "active"}

    def test_only_current_event(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_evento(env.session, OTHER_EVENT_ID)
        _crear_destino(env.session, "Córdoba")
        _crear_destino(env.session, "Otro Evento Destino", event_id=OTHER_EVENT_ID)

        response = env.client.get(f"{BASE}/exit-destinations")

        assert response.status_code == 200
        assert [d["name"] for d in response.json()] == ["Córdoba"]

    def test_includes_inactive(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_destino(env.session, "Activo", active=True)
        _crear_destino(env.session, "Inactivo", active=False)

        response = env.client.get(f"{BASE}/exit-destinations")

        assert response.status_code == 200
        activos = {d["name"]: d["active"] for d in response.json()}
        assert activos == {"Activo": True, "Inactivo": False}

    def test_404_unknown_event(self, env, auth_headers):
        response = env.client.get(f"{BASE}/exit-destinations")
        assert response.status_code == 404


class TestCreateExitDestination:

    def test_201_creates_with_payload(self, env, auth_headers):
        _crear_evento(env.session)

        response = env.client.post(
            f"{BASE}/exit-destinations",
            json={"name": "Córdoba", "active": False},
            headers=auth_headers,
        )

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Córdoba"
        assert body["active"] is False
        assert body["event_id"] == EVENT_ID
        assert body["id"]

    def test_active_defaults_to_true(self, env, auth_headers):
        _crear_evento(env.session)

        response = env.client.post(
            f"{BASE}/exit-destinations",
            json={"name": "Sinsacate"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        assert response.json()["active"] is True

    def test_409_duplicate_name_same_event(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_destino(env.session, "Córdoba")

        response = env.client.post(
            f"{BASE}/exit-destinations",
            json={"name": "Córdoba"},
            headers=auth_headers,
        )

        assert response.status_code == 409

    def test_duplicate_name_allowed_in_other_event(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_evento(env.session, OTHER_EVENT_ID)
        _crear_destino(env.session, "Córdoba")

        response = env.client.post(
            f"/api/events/{OTHER_EVENT_ID}/exit-destinations",
            json={"name": "Córdoba"},
            headers=auth_headers,
        )

        assert response.status_code == 201

    def test_404_unknown_event(self, env, auth_headers):
        response = env.client.post(
            f"{BASE}/exit-destinations",
            json={"name": "Córdoba"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_422_blank_name(self, env, auth_headers):
        _crear_evento(env.session)

        response = env.client.post(
            f"{BASE}/exit-destinations",
            json={"name": "   "},
            headers=auth_headers,
        )

        assert response.status_code == 422

    def test_401_without_token(self, env):
        _crear_evento(env.session)

        response = env.client.post(f"{BASE}/exit-destinations", json={"name": "Córdoba"})

        assert response.status_code == 401


class TestUpdateExitDestination:

    def test_renames(self, env, auth_headers):
        _crear_evento(env.session)
        destino = _crear_destino(env.session, "Cordoba")

        response = env.client.put(
            f"{BASE}/exit-destinations/{destino.id}",
            json={"name": "Córdoba"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Córdoba"
        env.session.expire_all()
        assert env.session.get(ExitDestination, destino.id).name == "Córdoba"

    def test_toggles_active(self, env, auth_headers):
        _crear_evento(env.session)
        destino = _crear_destino(env.session, "Córdoba", active=True)

        response = env.client.put(
            f"{BASE}/exit-destinations/{destino.id}",
            json={"active": False},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["active"] is False

    def test_partial_update_keeps_other_field(self, env, auth_headers):
        _crear_evento(env.session)
        destino = _crear_destino(env.session, "Córdoba", active=False)

        response = env.client.put(
            f"{BASE}/exit-destinations/{destino.id}",
            json={"active": True},
            headers=auth_headers,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["active"] is True
        assert body["name"] == "Córdoba"

    def test_409_rename_collides_with_existing(self, env, auth_headers):
        _crear_evento(env.session)
        destino = _crear_destino(env.session, "Córdoba")
        _crear_destino(env.session, "Sinsacate")

        response = env.client.put(
            f"{BASE}/exit-destinations/{destino.id}",
            json={"name": "Sinsacate"},
            headers=auth_headers,
        )

        assert response.status_code == 409

    def test_404_unknown_id(self, env, auth_headers):
        _crear_evento(env.session)

        response = env.client.put(
            f"{BASE}/exit-destinations/no-existe",
            json={"active": False},
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_404_destination_of_other_event(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_evento(env.session, OTHER_EVENT_ID)
        destino = _crear_destino(env.session, "De Otro Evento", event_id=OTHER_EVENT_ID)

        response = env.client.put(
            f"{BASE}/exit-destinations/{destino.id}",
            json={"active": False},
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_401_without_token(self, env):
        _crear_evento(env.session)
        destino = _crear_destino(env.session, "Córdoba")

        response = env.client.put(
            f"{BASE}/exit-destinations/{destino.id}", json={"active": False}
        )

        assert response.status_code == 401


class TestDeleteExitDestination:

    def test_204_and_removed_from_list(self, env, auth_headers):
        _crear_evento(env.session)
        destino = _crear_destino(env.session, "Córdoba")

        response = env.client.delete(
            f"{BASE}/exit-destinations/{destino.id}", headers=auth_headers
        )

        assert response.status_code == 204
        listing = env.client.get(f"{BASE}/exit-destinations").json()
        assert listing == []

    def test_delete_removes_zone_relations(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_salida(env.session)
        destino = _crear_destino(env.session, "Córdoba")
        _relacionar(env.session, ZONE_ID, destino.id)

        response = env.client.delete(
            f"{BASE}/exit-destinations/{destino.id}", headers=auth_headers
        )

        assert response.status_code == 204
        assert _destinos_de_zona(env, ZONE_ID) == []

    def test_404_unknown_id(self, env, auth_headers):
        _crear_evento(env.session)

        response = env.client.delete(
            f"{BASE}/exit-destinations/no-existe", headers=auth_headers
        )

        assert response.status_code == 404

    def test_404_destination_of_other_event(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_evento(env.session, OTHER_EVENT_ID)
        destino = _crear_destino(env.session, "De Otro Evento", event_id=OTHER_EVENT_ID)

        response = env.client.delete(
            f"{BASE}/exit-destinations/{destino.id}", headers=auth_headers
        )

        assert response.status_code == 404

    def test_401_without_token(self, env):
        _crear_evento(env.session)
        destino = _crear_destino(env.session, "Córdoba")

        response = env.client.delete(f"{BASE}/exit-destinations/{destino.id}")

        assert response.status_code == 401


class TestGetZoneExitDestinations:

    def test_returns_assigned_ids(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_salida(env.session)
        cordoba = _crear_destino(env.session, "Córdoba")
        sinsacate = _crear_destino(env.session, "Sinsacate")
        _relacionar(env.session, ZONE_ID, cordoba.id)
        _relacionar(env.session, ZONE_ID, sinsacate.id)

        response = env.client.get(f"{BASE}/zones/{ZONE_ID}/exit-destinations")

        assert response.status_code == 200
        body = response.json()
        assert body["zone_id"] == ZONE_ID
        assert sorted(body["destination_ids"]) == sorted([cordoba.id, sinsacate.id])

    def test_empty_when_no_relations(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_salida(env.session)

        response = env.client.get(f"{BASE}/zones/{ZONE_ID}/exit-destinations")

        assert response.status_code == 200
        assert response.json()["destination_ids"] == []

    def test_404_zone_of_other_event(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_evento(env.session, OTHER_EVENT_ID)
        _crear_salida(env.session, OTHER_ZONE_ID, event_id=OTHER_EVENT_ID)

        response = env.client.get(f"{BASE}/zones/{OTHER_ZONE_ID}/exit-destinations")

        assert response.status_code == 404


class TestUpdateZoneExitDestinations:

    def test_replaces_previous_relations(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_salida(env.session)
        cordoba = _crear_destino(env.session, "Córdoba")
        sinsacate = _crear_destino(env.session, "Sinsacate")
        caroya = _crear_destino(env.session, "Colonia Caroya")
        _relacionar(env.session, ZONE_ID, cordoba.id)
        _relacionar(env.session, ZONE_ID, sinsacate.id)

        response = env.client.put(
            f"{BASE}/zones/{ZONE_ID}/exit-destinations",
            json={"destination_ids": [caroya.id]},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json() == {"zone_id": ZONE_ID, "destination_ids": [caroya.id]}
        assert _destinos_de_zona(env, ZONE_ID) == [caroya.id]

    def test_empty_list_clears_relations(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_salida(env.session)
        cordoba = _crear_destino(env.session, "Córdoba")
        _relacionar(env.session, ZONE_ID, cordoba.id)

        response = env.client.put(
            f"{BASE}/zones/{ZONE_ID}/exit-destinations",
            json={"destination_ids": []},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["destination_ids"] == []
        assert _destinos_de_zona(env, ZONE_ID) == []

    def test_is_idempotent_on_repeat_calls(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_salida(env.session)
        cordoba = _crear_destino(env.session, "Córdoba")

        first = env.client.put(
            f"{BASE}/zones/{ZONE_ID}/exit-destinations",
            json={"destination_ids": [cordoba.id]},
            headers=auth_headers,
        )
        second = env.client.put(
            f"{BASE}/zones/{ZONE_ID}/exit-destinations",
            json={"destination_ids": [cordoba.id]},
            headers=auth_headers,
        )

        assert first.status_code == second.status_code == 200
        assert _destinos_de_zona(env, ZONE_ID) == [cordoba.id]

    def test_deduplicates_repeated_ids(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_salida(env.session)
        cordoba = _crear_destino(env.session, "Córdoba")
        sinsacate = _crear_destino(env.session, "Sinsacate")

        response = env.client.put(
            f"{BASE}/zones/{ZONE_ID}/exit-destinations",
            json={"destination_ids": [cordoba.id, sinsacate.id, cordoba.id]},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert sorted(response.json()["destination_ids"]) == sorted([cordoba.id, sinsacate.id])
        assert len(_destinos_de_zona(env, ZONE_ID)) == 2

    def test_preserves_order_of_requested_ids(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_salida(env.session)
        cordoba = _crear_destino(env.session, "Córdoba")
        sinsacate = _crear_destino(env.session, "Sinsacate")

        response = env.client.put(
            f"{BASE}/zones/{ZONE_ID}/exit-destinations",
            json={"destination_ids": [sinsacate.id, cordoba.id]},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.json()["destination_ids"] == [sinsacate.id, cordoba.id]

    def test_404_unknown_zone(self, env, auth_headers):
        _crear_evento(env.session)
        cordoba = _crear_destino(env.session, "Córdoba")

        response = env.client.put(
            f"{BASE}/zones/no-existe/exit-destinations",
            json={"destination_ids": [cordoba.id]},
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_404_unknown_destination_id(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_salida(env.session)
        cordoba = _crear_destino(env.session, "Córdoba")

        response = env.client.put(
            f"{BASE}/zones/{ZONE_ID}/exit-destinations",
            json={"destination_ids": [cordoba.id, "destino-fantasma"]},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert _destinos_de_zona(env, ZONE_ID) == []

    def test_404_destination_of_other_event(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_evento(env.session, OTHER_EVENT_ID)
        _crear_salida(env.session)
        ajeno = _crear_destino(env.session, "De Otro Evento", event_id=OTHER_EVENT_ID)

        response = env.client.put(
            f"{BASE}/zones/{ZONE_ID}/exit-destinations",
            json={"destination_ids": [ajeno.id]},
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert _destinos_de_zona(env, ZONE_ID) == []

    def test_401_without_token(self, env):
        _crear_evento(env.session)
        _crear_salida(env.session)
        cordoba = _crear_destino(env.session, "Córdoba")

        response = env.client.put(
            f"{BASE}/zones/{ZONE_ID}/exit-destinations",
            json={"destination_ids": [cordoba.id]},
        )

        assert response.status_code == 401
