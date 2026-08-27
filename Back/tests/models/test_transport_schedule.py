# backend/tests/models/test_transport_schedule.py
# S1 Transporte V1 - PARTE 3: tabla transport_schedules.
#
# Fixture propio: schema temporal desechable.
# Sin tablas geometry => no depende del PostGIS del entorno local.

import datetime
import uuid

import pytest
from sqlalchemy import create_engine, select, text, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import Base
from app.models.transport_line import TransportLine
from app.models.transport_line_stop import TransportLineStop
from app.models.transport_schedule import TransportSchedule


# ---------------------------------------------------------------------------
# Scratch schema DDL — no geometry columns
# ---------------------------------------------------------------------------
SCRATCH_DDL = """
CREATE TABLE events (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);
CREATE TABLE zones (
    id VARCHAR(36) PRIMARY KEY,
    event_id VARCHAR(36) NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    saturation VARCHAR(20) NOT NULL DEFAULT 'bajo',
    status VARCHAR(20) NOT NULL DEFAULT 'activa',
    capacity INTEGER NOT NULL DEFAULT 0,
    available_capacity INTEGER NOT NULL DEFAULT 0,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geometry TEXT,
    disponibilidad INTEGER,
    espera_min INTEGER,
    calle VARCHAR(255),
    subtipo VARCHAR(100),
    tipo_culinario VARCHAR(100),
    x DOUBLE PRECISION,
    y DOUBLE PRECISION,
    direccion VARCHAR(255),
    horario VARCHAR(100),
    telefono VARCHAR(50),
    web VARCHAR(255),
    servicios VARCHAR(500),
    transporte VARCHAR(50),
    capacidad_estimada INTEGER,
    es_embudo BOOLEAN,
    geometry_type VARCHAR(10) DEFAULT 'point',
    coordinates JSONB,
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);
CREATE TABLE transport_lines (
    id VARCHAR(36) PRIMARY KEY,
    event_id VARCHAR(36) NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'urbano',
    company VARCHAR(100),
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
    CONSTRAINT uq_transport_schedules_line_stop_schedule UNIQUE (line_stop_id, day_type, departure_time, destination)
);
CREATE INDEX idx_ts_line_stop ON transport_schedules (line_stop_id);
CREATE INDEX idx_ts_day_type ON transport_schedules (day_type);
"""


@pytest.fixture(scope="module")
def scratch_engine():
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS tmp_sched_model CASCADE"))
        conn.execute(text("CREATE SCHEMA tmp_sched_model"))
        conn.execute(text("SET LOCAL search_path TO tmp_sched_model"))
        conn.exec_driver_sql(SCRATCH_DDL)
        conn.commit()
    yield engine
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS tmp_sched_model CASCADE"))
        conn.commit()
    engine.dispose()


@pytest.fixture()
def db(scratch_engine):
    connection = scratch_engine.connect()
    transaction = connection.begin()
    connection.execute(text("SET search_path TO tmp_sched_model"))
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


def _get_relationships(model):
    return {rel.key: rel for rel in model.__mapper__.relationships}


# ---------------------------------------------------------------------------
# 1. Schema / structural tests (no DB needed)
# ---------------------------------------------------------------------------
class TestTransportScheduleSchema:
    """Estructura del modelo: tabla, columnas, constraints."""

    def test_table_name(self) -> None:
        assert TransportSchedule.__tablename__ == "transport_schedules"

    def test_inherits_base(self) -> None:
        assert issubclass(TransportSchedule, Base)

    def test_registered_in_base_metadata(self) -> None:
        assert "transport_schedules" in Base.metadata.tables

    def test_id_is_primary_key_string36(self) -> None:
        col = TransportSchedule.__table__.columns["id"]
        assert col.primary_key
        assert col.type.length == 36

    def test_line_stop_id_fk_with_cascade(self) -> None:
        col = TransportSchedule.__table__.columns["line_stop_id"]
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].target_fullname == "transport_line_stops.id"
        assert fks[0].ondelete == "CASCADE"

    def test_day_type_is_required_string20(self) -> None:
        col = TransportSchedule.__table__.columns["day_type"]
        assert col.nullable is False
        assert col.type.length == 20

    def test_departure_time_is_time_type(self) -> None:
        from sqlalchemy.types import Time as SATime
        col = TransportSchedule.__table__.columns["departure_time"]
        assert col.nullable is False
        assert isinstance(col.type, SATime)

    def test_destination_is_required_string100(self) -> None:
        col = TransportSchedule.__table__.columns["destination"]
        assert col.nullable is False
        assert col.type.length == 100

    def test_all_fields_not_null(self) -> None:
        for name in ("line_stop_id", "day_type", "departure_time", "destination"):
            col = TransportSchedule.__table__.columns[name]
            assert col.nullable is False, f"{name} should be NOT NULL"

    def test_unique_constraint_line_stop_schedule(self) -> None:
        uqs = [
            c for c in TransportSchedule.__table__.constraints
            if isinstance(c, UniqueConstraint)
        ]
        matching = [
            u for u in uqs
            if {c.name for c in u.columns} == {
                "line_stop_id", "day_type", "departure_time", "destination"
            }
        ]
        assert len(matching) == 1
        assert matching[0].name == "uq_transport_schedules_line_stop_schedule"

    def test_index_on_line_stop_id(self) -> None:
        index_names = {idx.name for idx in TransportSchedule.__table__.indexes}
        assert "idx_ts_line_stop" in index_names

    def test_index_on_day_type(self) -> None:
        index_names = {idx.name for idx in TransportSchedule.__table__.indexes}
        assert "idx_ts_day_type" in index_names


# ---------------------------------------------------------------------------
# 2. Relationship wiring tests
# ---------------------------------------------------------------------------
class TestRelationshipWiring:
    """Relaciones entre TransportLineStop y TransportSchedule."""

    def test_transport_line_stop_has_schedules_relationship(self) -> None:
        rels = _get_relationships(TransportLineStop)
        assert "schedules" in rels

    def test_transport_schedule_has_line_stop_relationship(self) -> None:
        rels = _get_relationships(TransportSchedule)
        assert "line_stop" in rels

    def test_back_populates(self) -> None:
        tls_rels = _get_relationships(TransportLineStop)
        ts_rels = _get_relationships(TransportSchedule)
        assert tls_rels["schedules"].back_populates == "line_stop"
        assert ts_rels["line_stop"].back_populates == "schedules"

    def test_relationship_target_is_transport_line_stop(self) -> None:
        ts_rels = _get_relationships(TransportSchedule)
        assert ts_rels["line_stop"].mapper.entity is TransportLineStop


# ---------------------------------------------------------------------------
# 3. Persistence tests (scratch schema, no geometry)
# ---------------------------------------------------------------------------
class TestTransportSchedulePersistence:
    """Comportamiento real contra Postgres (scratch schema sin geometry)."""

    def _make_event(self, session, event_id: str) -> None:
        session.execute(
            text("INSERT INTO events (id, name) VALUES (:id, :name)"),
            {"id": event_id, "name": f"Event {event_id[:8]}"},
        )
        session.flush()

    def _make_zone_raw(self, session, event_id: str, name: str = None) -> str:
        zone_id = str(uuid.uuid4())
        session.execute(
            text(
                "INSERT INTO zones (id, event_id, name, type, saturation, status, "
                "capacity, available_capacity) "
                "VALUES (:id, :event_id, :name, :type, :saturation, :status, "
                ":capacity, :available_capacity)"
            ),
            {"id": zone_id, "event_id": event_id,
             "name": name or f"Parada {uuid.uuid4().hex[:6]}",
             "type": "transporte", "saturation": "bajo", "status": "activa",
             "capacity": 300, "available_capacity": 300},
        )
        session.flush()
        return zone_id

    def _make_line(self, session, event_id: str) -> TransportLine:
        line = TransportLine(
            event_id=event_id,
            name=f"Línea {uuid.uuid4().hex[:6]}",
            type="urbano",
            company="Empresa A",
        )
        session.add(line)
        session.flush()
        return line

    def _make_line_stop(self, session, event_id: str, stop_order: int = 1) -> TransportLineStop:
        line = self._make_line(session, event_id)
        zone_id = self._make_zone_raw(session, event_id)
        tls = TransportLineStop(line_id=line.id, zone_id=zone_id, stop_order=stop_order)
        session.add(tls)
        session.flush()
        return tls

    def test_create_with_defaults(self, db) -> None:
        self._make_event(db, "evt-sched-1")
        tls = self._make_line_stop(db, "evt-sched-1")

        ts = TransportSchedule(
            line_stop_id=tls.id,
            day_type="weekday",
            departure_time=datetime.time(8, 0),
            destination="Terminal Central",
        )
        db.add(ts)
        db.flush()

        assert ts.id is not None
        assert len(ts.id) == 36
        assert ts.line_stop_id == tls.id
        assert ts.day_type == "weekday"
        assert ts.departure_time == datetime.time(8, 0)
        assert ts.destination == "Terminal Central"

    def test_cascade_delete_with_line_stop(self, db) -> None:
        self._make_event(db, "evt-sched-2")
        tls = self._make_line_stop(db, "evt-sched-2")

        db.add(TransportSchedule(
            line_stop_id=tls.id, day_type="weekday",
            departure_time=datetime.time(8, 0), destination="Terminal",
        ))
        db.add(TransportSchedule(
            line_stop_id=tls.id, day_type="weekday",
            departure_time=datetime.time(9, 0), destination="Terminal",
        ))
        db.flush()

        db.execute(text("DELETE FROM transport_line_stops WHERE id = :id"), {"id": tls.id})
        db.flush()

        remaining = db.execute(select(TransportSchedule)).scalars().all()
        assert remaining == []

    def test_unique_constraint_rejects_duplicates(self, db) -> None:
        self._make_event(db, "evt-sched-3")
        tls = self._make_line_stop(db, "evt-sched-3")

        db.add(TransportSchedule(
            line_stop_id=tls.id, day_type="weekday",
            departure_time=datetime.time(8, 0), destination="Terminal",
        ))
        db.flush()

        db.add(TransportSchedule(
            line_stop_id=tls.id, day_type="weekday",
            departure_time=datetime.time(8, 0), destination="Terminal",
        ))
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()

    def test_same_schedule_different_line_stops_allowed(self, db) -> None:
        self._make_event(db, "evt-sched-4")
        tls1 = self._make_line_stop(db, "evt-sched-4", stop_order=1)
        tls2 = self._make_line_stop(db, "evt-sched-4", stop_order=2)

        db.add(TransportSchedule(
            line_stop_id=tls1.id, day_type="weekday",
            departure_time=datetime.time(8, 0), destination="Terminal",
        ))
        db.add(TransportSchedule(
            line_stop_id=tls2.id, day_type="weekday",
            departure_time=datetime.time(8, 0), destination="Terminal",
        ))
        db.flush()

        all_schedules = db.execute(select(TransportSchedule)).scalars().all()
        assert len(all_schedules) == 2

    def test_same_line_stop_different_day_types_allowed(self, db) -> None:
        self._make_event(db, "evt-sched-5")
        tls = self._make_line_stop(db, "evt-sched-5")

        db.add(TransportSchedule(
            line_stop_id=tls.id, day_type="weekday",
            departure_time=datetime.time(8, 0), destination="Terminal",
        ))
        db.add(TransportSchedule(
            line_stop_id=tls.id, day_type="saturday",
            departure_time=datetime.time(8, 0), destination="Terminal",
        ))
        db.flush()

        all_schedules = db.execute(select(TransportSchedule)).scalars().all()
        assert len(all_schedules) == 2

    def test_same_line_stop_multiple_departures_same_day_type(self, db) -> None:
        self._make_event(db, "evt-sched-6")
        tls = self._make_line_stop(db, "evt-sched-6")

        db.add(TransportSchedule(
            line_stop_id=tls.id, day_type="weekday",
            departure_time=datetime.time(8, 0), destination="Terminal",
        ))
        db.add(TransportSchedule(
            line_stop_id=tls.id, day_type="weekday",
            departure_time=datetime.time(9, 0), destination="Terminal",
        ))
        db.flush()

        all_schedules = db.execute(select(TransportSchedule)).scalars().all()
        assert len(all_schedules) == 2

    def test_same_departure_different_destinations_allowed(self, db) -> None:
        self._make_event(db, "evt-sched-7")
        tls = self._make_line_stop(db, "evt-sched-7")

        db.add(TransportSchedule(
            line_stop_id=tls.id, day_type="weekday",
            departure_time=datetime.time(8, 0), destination="Terminal Norte",
        ))
        db.add(TransportSchedule(
            line_stop_id=tls.id, day_type="weekday",
            departure_time=datetime.time(8, 0), destination="Terminal Sur",
        ))
        db.flush()

        all_schedules = db.execute(select(TransportSchedule)).scalars().all()
        assert len(all_schedules) == 2
