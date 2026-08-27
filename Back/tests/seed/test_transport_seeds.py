# backend/tests/seed/test_transport_seeds.py
# PARTE 4 (S1 - Transporte V1): seeds de líneas, paradas y horarios.
#
# Estrategia: schema temporal desechable + rollback final. Las zonas se
# insertan con SQL crudo y el "evento" se simula con SimpleNamespace(id=...)
# porque el seed solo consume event.id — así ninguna query del test toca la
# columna geometry (PostGIS roto en el entorno local).

from datetime import time as dtime
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.transport_line import TransportLine
from app.models.transport_line_stop import TransportLineStop
from app.models.transport_schedule import TransportSchedule
from seed import (
    EVENT_ID,
    TRANSPORT_LINES_DATA,
    TRANSPORT_SCHEDULES_DATA,
    TRANSPORT_STOP_LINKS,
    seed_transport_data,
)

# IDs de zonas de transporte ya creadas por seed_zones()
PARADA_A_NAME = "Parada Línea A"
PARADA_B_NAME = "Parada Línea B"
PARADA_EXPRESS_NAME = "Parada Express"


# ---------------------------------------------------------------------------
# Constantes del seed
# ---------------------------------------------------------------------------
class TestSeedConstants:
    def test_exactamente_2_lineas(self) -> None:
        assert len(TRANSPORT_LINES_DATA) == 2

    def test_nombres_de_lineas(self) -> None:
        nombres = {ld["name"] for ld in TRANSPORT_LINES_DATA}
        assert nombres == {"Línea 100 Ejemplo", "Línea 200 Ejemplo"}

    def test_4_vinculos_parada_linea(self) -> None:
        assert len(TRANSPORT_STOP_LINKS) == 4

    def test_7_horarios(self) -> None:
        assert len(TRANSPORT_SCHEDULES_DATA) == 7


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


@pytest.fixture()
def seed_env():
    """Session ORM + conexión sobre un schema temporal (rollback final)."""
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    conn = engine.connect()
    trans = conn.begin()
    conn.execute(text("DROP SCHEMA IF EXISTS tmp_seed_transport CASCADE"))
    conn.execute(text("CREATE SCHEMA tmp_seed_transport"))
    conn.execute(text("SET LOCAL search_path TO tmp_seed_transport"))
    conn.exec_driver_sql(SCRATCH_DDL)
    conn.execute(
        text("INSERT INTO events (id, name) VALUES (:id, :name)"),
        {"id": EVENT_ID, "name": "Festival de Jesús María 2026"},
    )

    session = Session(bind=conn)
    try:
        yield session, conn
    finally:
        session.close()
        trans.rollback()
        conn.close()
        engine.dispose()


def _crear_paradas(conn, event_id):
    """Inserta las 3 zonas de transporte via raw SQL (sin geometry)."""
    paradas = [
        ("zone-parada-a", PARADA_A_NAME, 300, -30.973313, -64.088529),
        ("zone-parada-b", PARADA_B_NAME, 250, -30.978107, -64.094779),
        ("zone-parada-ex", PARADA_EXPRESS_NAME, 200, -30.985337, -64.094209),
    ]
    for zone_id, name, cap, lat, lng in paradas:
        conn.execute(
            text(
                "INSERT INTO zones (id, event_id, name, type, saturation, status, "
                "capacity, available_capacity, latitude, longitude) "
                "VALUES (:id, :event_id, :name, 'transporte', 'bajo', 'activa', "
                ":cap, :cap, :lat, :lng)"
            ),
            {"id": zone_id, "event_id": event_id, "name": name,
             "cap": cap, "lat": lat, "lng": lng},
        )


def _evento_fake():
    return SimpleNamespace(id=EVENT_ID)


# ---------------------------------------------------------------------------
# Tests de seeds de transporte
# ---------------------------------------------------------------------------
class TestSeedTransportLines:
    def test_crea_2_lineas(self, seed_env) -> None:
        session, conn = seed_env
        _crear_paradas(conn, EVENT_ID)

        resultado = seed_transport_data(session, _evento_fake())

        assert resultado["lines_created"] == 2
        lines = session.query(TransportLine).all()
        assert len(lines) == 2
        names = {l.name for l in lines}
        assert names == {"Línea 100 Ejemplo", "Línea 200 Ejemplo"}

    def test_atributos_correctos(self, seed_env) -> None:
        session, conn = seed_env
        _crear_paradas(conn, EVENT_ID)
        seed_transport_data(session, _evento_fake())

        l100 = session.query(TransportLine).filter_by(name="Línea 100 Ejemplo").one()
        assert l100.type == "interurbano"
        assert l100.company == "Empresa Ejemplo SRL"
        assert l100.color == "#FF5733"
        assert l100.event_id == EVENT_ID

        l200 = session.query(TransportLine).filter_by(name="Línea 200 Ejemplo").one()
        assert l200.type == "urbano"
        assert l200.company == "Transporte Urbano SA"
        assert l200.color == "#3498DB"
        assert l200.event_id == EVENT_ID

    def test_solo_para_event_id_objetivo(self, seed_env) -> None:
        session, conn = seed_env
        _crear_paradas(conn, EVENT_ID)
        # Crear zona en otro evento
        conn.execute(
            text("INSERT INTO events (id, name) VALUES (:id, :name)"),
            {"id": "other-event-000", "name": "Otro Evento"},
        )
        conn.execute(
            text(
                "INSERT INTO zones (id, event_id, name, type, saturation, status, "
                "capacity, available_capacity) "
                "VALUES ('zone-other', 'other-event-000', 'Parada Línea A', "
                "'transporte', 'bajo', 'activa', 300, 300)"
            ),
        )

        seed_transport_data(session, _evento_fake())

        other_lines = session.query(TransportLine).filter(
            TransportLine.event_id == "other-event-000"
        ).all()
        assert other_lines == []


class TestSeedTransportStops:
    def test_crea_4_paradas(self, seed_env) -> None:
        session, conn = seed_env
        _crear_paradas(conn, EVENT_ID)

        resultado = seed_transport_data(session, _evento_fake())

        assert resultado["stops_created"] == 4
        stops = session.query(TransportLineStop).all()
        assert len(stops) == 4

    def test_stop_order_correcto(self, seed_env) -> None:
        session, conn = seed_env
        _crear_paradas(conn, EVENT_ID)
        seed_transport_data(session, _evento_fake())

        l100 = session.query(TransportLine).filter_by(name="Línea 100 Ejemplo").one()
        l200 = session.query(TransportLine).filter_by(name="Línea 200 Ejemplo").one()

        # Línea 100: Parada A order 1, Parada B order 2
        stops_100 = session.query(TransportLineStop).filter_by(line_id=l100.id).all()
        stops_100_by_zone = {s.zone_id: s.stop_order for s in stops_100}
        zona_a = session.execute(
            select(text("id FROM zones WHERE name = :name AND event_id = :eid")),
            {"name": PARADA_A_NAME, "eid": EVENT_ID},
        ).scalar()
        zona_b = session.execute(
            select(text("id FROM zones WHERE name = :name AND event_id = :eid")),
            {"name": PARADA_B_NAME, "eid": EVENT_ID},
        ).scalar()
        assert stops_100_by_zone[zona_a] == 1
        assert stops_100_by_zone[zona_b] == 2

        # Línea 200: Parada A order 1, Parada Express order 2
        stops_200 = session.query(TransportLineStop).filter_by(line_id=l200.id).all()
        stops_200_by_zone = {s.zone_id: s.stop_order for s in stops_200}
        zona_ex = session.execute(
            select(text("id FROM zones WHERE name = :name AND event_id = :eid")),
            {"name": PARADA_EXPRESS_NAME, "eid": EVENT_ID},
        ).scalar()
        assert stops_200_by_zone[zona_a] == 1
        assert stops_200_by_zone[zona_ex] == 2


class TestSeedTransportSchedules:
    def test_crea_7_horarios(self, seed_env) -> None:
        session, conn = seed_env
        _crear_paradas(conn, EVENT_ID)

        resultado = seed_transport_data(session, _evento_fake())

        assert resultado["schedules_created"] == 7
        schedules = session.query(TransportSchedule).all()
        assert len(schedules) == 7

    def test_horarios_asociados_a_line_stop_correcto(self, seed_env) -> None:
        session, conn = seed_env
        _crear_paradas(conn, EVENT_ID)
        seed_transport_data(session, _evento_fake())

        l100 = session.query(TransportLine).filter_by(name="Línea 100 Ejemplo").one()
        zona_a_id = session.execute(
            select(text("id FROM zones WHERE name = :name AND event_id = :eid")),
            {"name": PARADA_A_NAME, "eid": EVENT_ID},
        ).scalar()

        tls_a = session.query(TransportLineStop).filter_by(
            line_id=l100.id, zone_id=zona_a_id,
        ).one()

        schedules_a = session.query(TransportSchedule).filter_by(
            line_stop_id=tls_a.id,
        ).all()
        assert len(schedules_a) == 2
        times = sorted(s.departure_time for s in schedules_a)
        assert times == [dtime(10, 15), dtime(11, 30)]
        assert all(s.destination == "Córdoba" for s in schedules_a)


class TestSeedTransportIdempotency:
    def test_ejecutar_2_veces_no_duplica(self, seed_env) -> None:
        session, conn = seed_env
        _crear_paradas(conn, EVENT_ID)

        primera = seed_transport_data(session, _evento_fake())
        segunda = seed_transport_data(session, _evento_fake())

        assert primera["lines_created"] == 2
        assert segunda["lines_created"] == 0
        assert segunda["stops_created"] == 0
        assert segunda["schedules_created"] == 0

        assert session.query(TransportLine).count() == 2
        assert session.query(TransportLineStop).count() == 4
        assert session.query(TransportSchedule).count() == 7

    def test_3_ejecuciones_seguidas_sin_error(self, seed_env) -> None:
        session, conn = seed_env
        _crear_paradas(conn, EVENT_ID)

        for _ in range(3):
            seed_transport_data(session, _evento_fake())

        assert session.query(TransportLine).count() == 2
        assert session.query(TransportLineStop).count() == 4
        assert session.query(TransportSchedule).count() == 7
