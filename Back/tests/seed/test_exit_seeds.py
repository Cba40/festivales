# backend/tests/seed/test_exit_seeds.py
# PARTE 4 (S1 - Salir V1): seeds de destinos + relaciones N:N.
#
# Estrategia: schema temporal desechable + rollback final. Las zonas se
# insertan con SQL crudo y el "evento" se simula con SimpleNamespace(id=...)
# porque el seed solo lee event.id — así ninguna query del test toca la
# columna geometry (PostGIS roto en el entorno local, ver Parte 1).

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from seed import (
    EVENT_ID,
    EXIT_DESTINATION_NAMES,
    EXIT_ZONE_DESTINATIONS,
    seed_exit_destinations,
    seed_exit_zone_destinations,
)
from app.models.exit_destination import ExitDestination
from app.models.exit_zone_destination import exit_zone_destinations_table

NORTE_ID = "b8a6ff92-0fce-4a53-8262-20b0c2d05f0c"
SUR_ID = "4a2fbeef-b6d0-4530-8a5e-b192853f5d56"


class TestSeedConstants:
    """Sin inventar zonas ni destinos: solo lo acordado en el RFC."""

    def test_exactamente_4_destinos(self) -> None:
        assert sorted(EXIT_DESTINATION_NAMES) == sorted(
            ["Córdoba", "Colonia Caroya", "Sinsacate", "Sierras Chicas"]
        )

    def test_solo_las_dos_salidas_de_produccion(self) -> None:
        assert set(EXIT_ZONE_DESTINATIONS.keys()) == {NORTE_ID, SUR_ID}

    def test_relaciones_acordadas(self) -> None:
        assert EXIT_ZONE_DESTINATIONS[NORTE_ID] == ["Córdoba", "Colonia Caroya", "Sinsacate"]
        assert EXIT_ZONE_DESTINATIONS[SUR_ID] == ["Sierras Chicas"]


SCRATCH_DDL = """
CREATE TABLE events (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255)
);
CREATE TABLE zones (
    id VARCHAR(36) PRIMARY KEY,
    event_id VARCHAR(36) REFERENCES events(id),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL
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
def seed_env():
    """Session ORM + conexión sobre un schema temporal (rollback final)."""
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    conn = engine.connect()
    trans = conn.begin()
    conn.execute(text("DROP SCHEMA IF EXISTS tmp_seed_test CASCADE"))
    conn.execute(text("CREATE SCHEMA tmp_seed_test"))
    conn.execute(text("SET LOCAL search_path TO tmp_seed_test"))
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


def _crear_salidas(conn, norte_type="salida", sur_type="salida"):
    for zone_id, name, ztype in (
        (NORTE_ID, "Salida Norte Auto", norte_type),
        (SUR_ID, "Salida Sur Peatonal", sur_type),
    ):
        conn.execute(
            text(
                "INSERT INTO zones (id, event_id, name, type) "
                "VALUES (:id, :event_id, :name, :type)"
            ),
            {"id": zone_id, "event_id": EVENT_ID, "name": name, "type": ztype},
        )


def _evento_fake():
    # El seed solo consume event.id
    return SimpleNamespace(id=EVENT_ID)


def _destinos_por_nombre(session):
    return {d.name: d.id for d in session.query(ExitDestination).all()}


def _relaciones(session):
    rows = session.execute(select(exit_zone_destinations_table)).all()
    return {(r.exit_zone_id, r.destination_id) for r in rows}


class TestSeedExitDestinations:
    def test_crea_exactamente_4_destinos_activos(self, seed_env) -> None:
        session, _conn = seed_env
        resultado = seed_exit_destinations(session, _evento_fake())

        assert resultado == {"created": 4, "skipped": 0}
        destinos = session.query(ExitDestination).all()
        assert len(destinos) == 4
        assert {d.name for d in destinos} == set(EXIT_DESTINATION_NAMES)
        assert all(d.active is True for d in destinos)
        assert all(d.event_id == EVENT_ID for d in destinos)

    def test_skip_sin_errores_si_ya_existen(self, seed_env) -> None:
        session, _conn = seed_env
        primera = seed_exit_destinations(session, _evento_fake())
        segunda = seed_exit_destinations(session, _evento_fake())

        assert primera == {"created": 4, "skipped": 0}
        assert segunda == {"created": 0, "skipped": 4}
        assert session.query(ExitDestination).count() == 4


class TestSeedExitZoneDestinations:
    def test_crea_las_4_relaciones_especificas(self, seed_env) -> None:
        session, conn = seed_env
        _crear_salidas(conn)
        seed_exit_destinations(session, _evento_fake())

        creadas = seed_exit_zone_destinations(session)

        destinos = _destinos_por_nombre(session)
        esperadas = {
            (NORTE_ID, destinos["Córdoba"]),
            (NORTE_ID, destinos["Colonia Caroya"]),
            (NORTE_ID, destinos["Sinsacate"]),
            (SUR_ID, destinos["Sierras Chicas"]),
        }
        assert len(creadas) == 4
        relaciones = _relaciones(session)
        assert relaciones == esperadas
        # La salida peatonal NO se relaciona con destinos vehiculares
        assert (SUR_ID, destinos["Córdoba"]) not in relaciones
        assert (SUR_ID, destinos["Sinsacate"]) not in relaciones

    def test_zona_no_salida_no_recibe_relaciones(self, seed_env) -> None:
        session, conn = seed_env
        _crear_salidas(conn, norte_type="estacionamiento")
        seed_exit_destinations(session, _evento_fake())

        creadas = seed_exit_zone_destinations(session)

        destinos = _destinos_por_nombre(session)
        esperada = {(SUR_ID, destinos["Sierras Chicas"])}
        assert creadas == [(SUR_ID, destinos["Sierras Chicas"])]
        assert _relaciones(session) == esperada

    def test_zonas_inexistentes_no_explotan(self, seed_env) -> None:
        session, _conn = seed_env
        seed_exit_destinations(session, _evento_fake())

        creadas = seed_exit_zone_destinations(session)

        assert creadas == []
        assert _relaciones(session) == set()

    def test_idempotencia_n_ejecuciones(self, seed_env) -> None:
        session, conn = seed_env
        _crear_salidas(conn)
        seed_exit_destinations(session, _evento_fake())

        primera = seed_exit_zone_destinations(session)
        segunda = seed_exit_zone_destinations(session)
        tercera = seed_exit_zone_destinations(session)

        assert len(primera) == 4
        assert segunda == []
        assert tercera == []
        assert len(_relaciones(session)) == 4
