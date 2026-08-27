# backend/tests/api/routes/test_transport_admin.py
# Tests de gestión administrativa de Transporte V1 (Dashboard > Infraestructura > Transporte).
# Endpoints cubiertos:
#   GET/POST /api/events/{event_id}/transport-lines
#   PUT/DELETE /api/events/{event_id}/transport-lines/{id}
#   GET/PUT /api/events/{event_id}/transport-lines/{id}/stops
#   GET/PUT /api/events/{event_id}/transport-lines/{id}/schedules
#   POST /api/events/{event_id}/transport/import-csv
#
# Fixture propio: esquema temporal desechable sin geometría => no depende del
# PostGIS local (misma estrategia que test_exit_admin.py).

from datetime import datetime, timedelta, timezone
from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.main import app

EVENT_ID = "event-transport-admin-a"
OTHER_EVENT_ID = "event-transport-admin-b"
LINE_ID = "line-a"
LINE_ID_B = "line-b"
ZONE_A = "zone-t1"
ZONE_B = "zone-t2"
ZONE_OTHER_TYPE = "zone-comida"

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
    type VARCHAR(100) NOT NULL
);
CREATE TABLE transport_lines (
    id VARCHAR(36) PRIMARY KEY,
    event_id VARCHAR(36) NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    type VARCHAR(20) NOT NULL,
    company VARCHAR(100) NOT NULL,
    color VARCHAR(7),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    CONSTRAINT uq_transport_lines_event_name UNIQUE (event_id, name)
);
CREATE TABLE transport_line_stops (
    id VARCHAR(36) PRIMARY KEY,
    line_id VARCHAR(36) NOT NULL REFERENCES transport_lines(id) ON DELETE CASCADE,
    zone_id VARCHAR(36) NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    stop_order INTEGER NOT NULL,
    CONSTRAINT uq_transport_line_stops_line_zone UNIQUE (line_id, zone_id),
    CONSTRAINT uq_transport_line_stops_line_order UNIQUE (line_id, stop_order)
);
CREATE TABLE transport_schedules (
    id VARCHAR(36) PRIMARY KEY,
    line_stop_id VARCHAR(36) NOT NULL REFERENCES transport_line_stops(id) ON DELETE CASCADE,
    day_type VARCHAR(20) NOT NULL,
    departure_time TIME NOT NULL,
    destination VARCHAR(100) NOT NULL,
    CONSTRAINT uq_transport_schedules_line_stop_schedule
        UNIQUE (line_stop_id, day_type, departure_time, destination)
);
"""


@pytest.fixture()
def env():
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    connection = engine.connect()
    transaction = connection.begin()
    connection.exec_driver_sql("DROP SCHEMA IF EXISTS tmp_transport_admin CASCADE")
    connection.exec_driver_sql("CREATE SCHEMA tmp_transport_admin")
    connection.execute(text("SET LOCAL search_path TO tmp_transport_admin"))
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


def _crear_zona(session: Session, zone_id: str, name: str, event_id: str = EVENT_ID, type: str = "transporte") -> None:
    session.execute(
        text("INSERT INTO zones (id, event_id, name, type) VALUES (:id, :eid, :name, :type)"),
        {"id": zone_id, "eid": event_id, "name": name, "type": type},
    )
    session.flush()


def _crear_linea(
    session: Session,
    event_id: str = EVENT_ID,
    line_id: str = LINE_ID,
    name: str = "Linea A",
    type: str = "urbano",
    company: str = "Empresa A",
    active: bool = True,
) -> str:
    session.execute(
        text(
            "INSERT INTO transport_lines (id, event_id, name, type, company, color, active) "
            "VALUES (:id, :eid, :name, :type, :company, NULL, :active)"
        ),
        {"id": line_id, "eid": event_id, "name": name, "type": type, "company": company, "active": active},
    )
    session.flush()
    return line_id


def _crear_stop(session: Session, line_id: str, zone_id: str, stop_order: int) -> str:
    stop_id = f"stop-{line_id}-{zone_id}"
    session.execute(
        text(
            "INSERT INTO transport_line_stops (id, line_id, zone_id, stop_order) "
            "VALUES (:id, :line_id, :zone_id, :stop_order)"
        ),
        {"id": stop_id, "line_id": line_id, "zone_id": zone_id, "stop_order": stop_order},
    )
    session.flush()
    return stop_id


def _crear_schedule(
    session: Session,
    line_stop_id: str,
    day_type: str = "weekday",
    departure_time: str = "08:00",
    destination: str = "Centro",
) -> str:
    sched_id = f"sched-{line_stop_id}-{departure_time.replace(':', '')}"
    session.execute(
        text(
            "INSERT INTO transport_schedules (id, line_stop_id, day_type, departure_time, destination) "
            "VALUES (:id, :lsid, :day_type, :dt, :dest)"
        ),
        {
            "id": sched_id,
            "lsid": line_stop_id,
            "day_type": day_type,
            "dt": departure_time,
            "dest": destination,
        },
    )
    session.flush()
    return sched_id


def _count(session: Session, table: str) -> int:
    return session.execute(text(f"SELECT count(*) FROM {table}")).scalar()


def _linea_ids(session: Session) -> list[str]:
    rows = session.execute(text("SELECT id FROM transport_lines ORDER BY name")).scalars().all()
    return list(rows)


# --------------------------------------------------------------------------
# Líneas
# --------------------------------------------------------------------------


class TestLineCRUD:

    def test_empty_list(self, env, auth_headers):
        _crear_evento(env.session)
        response = env.client.get(f"{BASE}/transport-lines")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_and_list(self, env, auth_headers):
        _crear_evento(env.session)
        created = env.client.post(
            f"{BASE}/transport-lines",
            json={"name": "Linea 1", "type": "urbano", "company": "Empresa X", "color": "#ff0000"},
            headers=auth_headers,
        )
        assert created.status_code == 201
        body = created.json()
        assert body["name"] == "Linea 1"
        assert body["type"] == "urbano"
        assert body["company"] == "Empresa X"
        assert body["color"] == "#ff0000"
        assert body["active"] is True
        assert body["id"]

        listing = env.client.get(f"{BASE}/transport-lines").json()
        assert [l["name"] for l in listing] == ["Linea 1"]
        assert set(listing[0].keys()) == {"id", "event_id", "name", "type", "company", "color", "active"}

    def test_create_default_active(self, env, auth_headers):
        _crear_evento(env.session)
        response = env.client.post(
            f"{BASE}/transport-lines",
            json={"name": "Linea 2", "type": "interurbano", "company": "Empresa Y"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["active"] is True

    def test_409_duplicate_name_same_event(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_linea(env.session)
        response = env.client.post(
            f"{BASE}/transport-lines",
            json={"name": "Linea A", "type": "urbano", "company": "Otra"},
            headers=auth_headers,
        )
        assert response.status_code == 409

    def test_duplicate_name_allowed_in_other_event(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_evento(env.session, OTHER_EVENT_ID)
        _crear_linea(env.session)
        response = env.client.post(
            f"/api/events/{OTHER_EVENT_ID}/transport-lines",
            json={"name": "Linea A", "type": "urbano", "company": "Otra"},
            headers=auth_headers,
        )
        assert response.status_code == 201

    def test_update_line(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session, name="Linea A", type="urbano", company="Antigua")
        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}",
            json={"name": "Linea B", "type": "interurbano", "company": "Nueva", "active": False},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "Linea B"
        assert body["type"] == "interurbano"
        assert body["company"] == "Nueva"
        assert body["active"] is False

    def test_update_toggle_active_only(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session, name="Linea A", active=True)
        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}", json={"active": False}, headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["active"] is False
        assert response.json()["name"] == "Linea A"

    def test_409_rename_collides(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_linea(env.session, line_id=LINE_ID, name="Linea A")
        _crear_linea(env.session, line_id=LINE_ID_B, name="Linea B")
        response = env.client.put(
            f"{BASE}/transport-lines/{LINE_ID}", json={"name": "Linea B"}, headers=auth_headers
        )
        assert response.status_code == 409

    def test_delete_line(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        response = env.client.delete(f"{BASE}/transport-lines/{line_id}", headers=auth_headers)
        assert response.status_code == 204
        assert env.client.get(f"{BASE}/transport-lines").json() == []

    def test_cascade_delete_removes_stops_and_schedules(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        _crear_zona(env.session, ZONE_A, "Parada Norte")
        stop_id = _crear_stop(env.session, line_id, ZONE_A, 1)
        _crear_schedule(env.session, stop_id)

        response = env.client.delete(f"{BASE}/transport-lines/{line_id}", headers=auth_headers)
        assert response.status_code == 204
        env.session.flush()
        assert _count(env.session, "transport_line_stops") == 0
        assert _count(env.session, "transport_schedules") == 0

    def test_404_unknown_event(self, env, auth_headers):
        response = env.client.get(f"{BASE}/transport-lines")
        assert response.status_code == 404

    def test_404_line_of_other_event(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_evento(env.session, OTHER_EVENT_ID)
        line_id = _crear_linea(env.session, event_id=OTHER_EVENT_ID)
        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}", json={"active": False}, headers=auth_headers
        )
        assert response.status_code == 404

    def test_404_unknown_line(self, env, auth_headers):
        _crear_evento(env.session)
        response = env.client.delete(f"{BASE}/transport-lines/no-existe", headers=auth_headers)
        assert response.status_code == 404

    def test_401_write_without_token(self, env):
        _crear_evento(env.session)
        assert env.client.post(
            f"{BASE}/transport-lines", json={"name": "X", "type": "urbano", "company": "Y"}
        ).status_code == 401


# --------------------------------------------------------------------------
# Paradas
# --------------------------------------------------------------------------


class TestStops:

    def test_stops_include_zone_name(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        _crear_zona(env.session, ZONE_A, "Parada Norte")
        stop_id = _crear_stop(env.session, line_id, ZONE_A, 1)

        response = env.client.get(f"{BASE}/transport-lines/{line_id}/stops")
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["id"] == stop_id
        assert body[0]["zone_id"] == ZONE_A
        assert body[0]["zone_name"] == "Parada Norte"
        assert body[0]["stop_order"] == 1

    def test_put_replaces_stops(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        _crear_zona(env.session, ZONE_A, "Parada Norte")
        _crear_zona(env.session, ZONE_B, "Parada Sur")
        _crear_stop(env.session, line_id, ZONE_A, 1)

        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}/stops",
            json={"stops": [{"zone_id": ZONE_B, "stop_order": 5}, {"zone_id": ZONE_A, "stop_order": 2}]},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert [(s["zone_id"], s["stop_order"]) for s in body] == [(ZONE_A, 2), (ZONE_B, 5)]
        assert _count(env.session, "transport_line_stops") == 2

    def test_put_clears_stops_with_empty_list(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        _crear_zona(env.session, ZONE_A, "Parada Norte")
        _crear_stop(env.session, line_id, ZONE_A, 1)

        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}/stops", json={"stops": []}, headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json() == []
        assert _count(env.session, "transport_line_stops") == 0

    def test_put_422_unknown_zone(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}/stops",
            json={"stops": [{"zone_id": "fantasma", "stop_order": 1}]},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_put_422_zone_not_transporte(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        _crear_zona(env.session, ZONE_OTHER_TYPE, "Puesto", type="comida")
        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}/stops",
            json={"stops": [{"zone_id": ZONE_OTHER_TYPE, "stop_order": 1}]},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_put_422_zone_of_other_event(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_evento(env.session, OTHER_EVENT_ID)
        line_id = _crear_linea(env.session)
        _crear_zona(env.session, ZONE_A, "Otra", event_id=OTHER_EVENT_ID)
        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}/stops",
            json={"stops": [{"zone_id": ZONE_A, "stop_order": 1}]},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_put_422_duplicate_stop_order(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        _crear_zona(env.session, ZONE_A, "Norte")
        _crear_zona(env.session, ZONE_B, "Sur")
        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}/stops",
            json={
                "stops": [
                    {"zone_id": ZONE_A, "stop_order": 1},
                    {"zone_id": ZONE_B, "stop_order": 1},
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_404_stops_line_of_other_event(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_evento(env.session, OTHER_EVENT_ID)
        line_id = _crear_linea(env.session, event_id=OTHER_EVENT_ID)
        response = env.client.get(f"{BASE}/transport-lines/{line_id}/stops")
        assert response.status_code == 404

    def test_401_put_stops_without_token(self, env):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}/stops", json={"stops": []}
        )
        assert response.status_code == 401


# --------------------------------------------------------------------------
# Horarios
# --------------------------------------------------------------------------


class TestSchedules:

    def test_schedules_ordered_by_day_type_and_time(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        _crear_zona(env.session, ZONE_A, "Parada Norte")
        stop_id = _crear_stop(env.session, line_id, ZONE_A, 1)
        _crear_schedule(env.session, stop_id, "saturday", "10:00", "Centro")
        _crear_schedule(env.session, stop_id, "weekday", "07:00", "Centro")
        _crear_schedule(env.session, stop_id, "weekday", "08:00", "Centro")
        _crear_schedule(env.session, stop_id, "sunday_holiday", "09:00", "Centro")

        response = env.client.get(f"{BASE}/transport-lines/{line_id}/schedules")
        assert response.status_code == 200
        body = response.json()
        days = [s["day_type"] for s in body]
        assert days == ["saturday", "sunday_holiday", "weekday", "weekday"]
        assert [s["departure_time"] for s in body][:2] == ["10:00", "09:00"]
        assert [s["departure_time"] for s in body][2:] == ["07:00", "08:00"]
        for s in body:
            assert set(s.keys()) == {"id", "line_stop_id", "day_type", "departure_time", "destination"}

    def test_put_replaces_schedules(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        _crear_zona(env.session, ZONE_A, "Norte")
        stop_id = _crear_stop(env.session, line_id, ZONE_A, 1)
        _crear_schedule(env.session, stop_id, "weekday", "08:00", "Viejo")

        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}/schedules",
            json={
                "schedules": [
                    {
                        "line_stop_id": stop_id,
                        "day_type": "weekday",
                        "departure_time": "08:30",
                        "destination": "Centro",
                    }
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["departure_time"] == "08:30"
        assert body[0]["destination"] == "Centro"
        assert body[0]["line_stop_id"] == stop_id
        assert _count(env.session, "transport_schedules") == 1

    def test_put_clears_all_schedules(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        _crear_zona(env.session, ZONE_A, "Norte")
        stop_id = _crear_stop(env.session, line_id, ZONE_A, 1)
        _crear_schedule(env.session, stop_id)
        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}/schedules",
            json={"schedules": []},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json() == []
        assert _count(env.session, "transport_schedules") == 0

    def test_put_422_line_stop_not_in_line(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        other = _crear_linea(env.session, line_id=LINE_ID_B, name="Otra")
        _crear_zona(env.session, ZONE_A, "Norte")
        foreign_stop = _crear_stop(env.session, other, ZONE_A, 1)

        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}/schedules",
            json={
                "schedules": [
                    {
                        "line_stop_id": foreign_stop,
                        "day_type": "weekday",
                        "departure_time": "08:00",
                        "destination": "Centro",
                    }
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_put_422_invalid_time_format(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        _crear_zona(env.session, ZONE_A, "Norte")
        stop_id = _crear_stop(env.session, line_id, ZONE_A, 1)

        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}/schedules",
            json={
                "schedules": [
                    {
                        "line_stop_id": stop_id,
                        "day_type": "weekday",
                        "departure_time": "25:99",
                        "destination": "Centro",
                    }
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_put_422_invalid_day_type(self, env, auth_headers):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        _crear_zona(env.session, ZONE_A, "Norte")
        stop_id = _crear_stop(env.session, line_id, ZONE_A, 1)

        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}/schedules",
            json={
                "schedules": [
                    {
                        "line_stop_id": stop_id,
                        "day_type": "feriado",
                        "departure_time": "08:00",
                        "destination": "Centro",
                    }
                ]
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_404_schedules_line_of_other_event(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_evento(env.session, OTHER_EVENT_ID)
        line_id = _crear_linea(env.session, event_id=OTHER_EVENT_ID)
        response = env.client.get(f"{BASE}/transport-lines/{line_id}/schedules")
        assert response.status_code == 404

    def test_401_put_schedules_without_token(self, env):
        _crear_evento(env.session)
        line_id = _crear_linea(env.session)
        response = env.client.put(
            f"{BASE}/transport-lines/{line_id}/schedules", json={"schedules": []}
        )
        assert response.status_code == 401


# --------------------------------------------------------------------------
# Importación CSV
# --------------------------------------------------------------------------


class TestCsvImport:

    CSV_HEADER = (
        "line_name,line_type,company,stop_name,stop_order,day_type,departure_time,destination"
    )

    def _post_csv(self, env, content: str, headers=None):
        return env.client.post(
            f"{BASE}/transport/import-csv",
            files={"file": ("data.csv", content, "text/csv")},
            headers=headers or {},
        )

    def test_creates_lines_stops_schedules(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_zona(env.session, ZONE_A, "Parada Norte")
        _crear_zona(env.session, ZONE_B, "Parada Sur")

        csv_content = "\n".join([
            self.CSV_HEADER,
            "Linea 1,urbano,Empresa A,Parada Norte,1,weekday,08:00,Centro",
            "Linea 1,urbano,Empresa A,Parada Sur,2,weekday,08:15,Centro",
        ])
        response = self._post_csv(env, csv_content, auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["lines_created"] == 1
        assert body["lines_updated"] == 0
        assert body["stops_created"] == 2
        assert body["schedules_created"] == 2
        assert body["errors"] == []

        lines = env.client.get(f"{BASE}/transport-lines").json()
        assert len(lines) == 1
        assert lines[0]["name"] == "Linea 1"

        line_id = lines[0]["id"]
        stops = env.client.get(f"{BASE}/transport-lines/{line_id}/stops").json()
        assert len(stops) == 2
        schedules = env.client.get(f"{BASE}/transport-lines/{line_id}/schedules").json()
        assert len(schedules) == 2

    def test_is_idempotent(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_zona(env.session, ZONE_A, "Parada Norte")
        csv_content = "\n".join([
            self.CSV_HEADER,
            "Linea 1,urbano,Empresa A,Parada Norte,1,weekday,08:00,Centro",
        ])

        first = self._post_csv(env, csv_content, auth_headers).json()
        second = self._post_csv(env, csv_content, auth_headers).json()

        assert first["lines_created"] == 1
        assert first["stops_created"] == 1
        assert first["schedules_created"] == 1

        assert second["lines_created"] == 0
        assert second["stops_created"] == 0
        assert second["schedules_created"] == 0

        assert _count(env.session, "transport_lines") == 1
        assert _count(env.session, "transport_line_stops") == 1
        assert _count(env.session, "transport_schedules") == 1

    def test_updates_existing_line_type(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_zona(env.session, ZONE_A, "Parada Norte")
        csv_content = "\n".join([
            self.CSV_HEADER,
            "Linea 1,urbano,Empresa A,Parada Norte,1,weekday,08:00,Centro",
        ])
        self._post_csv(env, csv_content, auth_headers)
        inter_content = "\n".join([
            self.CSV_HEADER,
            "Linea 1,interurbano,Empresa A,Parada Norte,1,weekday,08:00,Centro",
        ])
        response = self._post_csv(env, inter_content, auth_headers).json()
        assert response["lines_updated"] == 1
        assert env.client.get(f"{BASE}/transport-lines").json()[0]["type"] == "interurbano"

    def test_skips_row_with_unknown_zone(self, env, auth_headers):
        _crear_evento(env.session)
        _crear_zona(env.session, ZONE_A, "Parada Norte")
        csv_content = "\n".join([
            self.CSV_HEADER,
            "Linea 1,urbano,Empresa A,Parada Inexistente,1,weekday,08:00,Centro",
            "Linea 1,urbano,Empresa A,Parada Norte,2,weekday,08:15,Centro",
        ])
        response = self._post_csv(env, csv_content, auth_headers).json()
        assert response["lines_created"] == 1
        assert response["stops_created"] == 1
        assert response["schedules_created"] == 1
        assert len(response["errors"]) == 1

    def test_422_missing_columns(self, env, auth_headers):
        _crear_evento(env.session)
        response = self._post_csv(env, "line_name,company\na,b\n", auth_headers)
        assert response.status_code == 422

    def test_401_without_token(self, env):
        _crear_evento(env.session)
        csv_content = self.CSV_HEADER + "\n"
        response = self._post_csv(env, csv_content)
        assert response.status_code == 401

    def test_404_unknown_event(self, env, auth_headers):
        response = self._post_csv(env, self.CSV_HEADER + "\n", auth_headers)
        assert response.status_code == 404
