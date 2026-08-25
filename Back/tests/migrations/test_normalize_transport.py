# backend/tests/migrations/test_normalize_transport.py
# PARTE 3 (S1 - Salir V1): normalización de zones.transporte.

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app.core.config import settings
from seed import ZONES_DATA

MIGRATION_FILENAME = "c9d3e7f1a5b8_normalize_zones_transport_mode.py"
MIGRATION_PATH = (
    Path(__file__).resolve().parents[2] / "alembic" / "versions" / MIGRATION_FILENAME
)

FORBIDDEN_UPDATE_TOKENS = ("latitude", "longitude", "capacity", "name =", "SET name")


def _load_migration():
    spec = importlib.util.spec_from_file_location("normalize_transport", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestMigrationStructure:
    def test_revision_chain(self) -> None:
        mod = _load_migration()
        assert mod.revision == "c9d3e7f1a5b8"
        assert mod.down_revision == "f4a6b8c0d2e4"

    def test_upgrade_has_two_statements(self) -> None:
        mod = _load_migration()
        assert len(mod.UPGRADE_STATEMENTS) == 2
        assert all(isinstance(s, str) for s in mod.UPGRADE_STATEMENTS)

    def test_downgrade_reverts_vehicular_to_auto(self) -> None:
        mod = _load_migration()
        assert len(mod.DOWNGRADE_STATEMENTS) == 1
        assert "SET transporte = 'auto'" in mod.DOWNGRADE_STATEMENTS[0]
        assert "LOWER(TRIM(transporte)) = 'vehicular'" in mod.DOWNGRADE_STATEMENTS[0]


class TestMigrationSafety:
    """El UPDATE solo toca zones.transporte y solo filas type='salida'."""

    def test_all_statements_update_only_transporte_on_salidas(self) -> None:
        mod = _load_migration()
        statements = list(mod.UPGRADE_STATEMENTS) + list(mod.DOWNGRADE_STATEMENTS)
        assert statements, "la migración debe definir sentencias"
        for stmt in statements:
            normalized = " ".join(stmt.split())
            assert "UPDATE zones" in normalized
            assert "SET transporte =" in normalized
            assert "WHERE type = 'salida'" in normalized

    def test_no_forbidden_columns_touched(self) -> None:
        mod = _load_migration()
        statements = list(mod.UPGRADE_STATEMENTS) + list(mod.DOWNGRADE_STATEMENTS)
        for stmt in statements:
            lowered = stmt.lower()
            for token in FORBIDDEN_UPDATE_TOKENS:
                assert token not in lowered, f"token prohibido: {token}"

    def test_upgrade_covers_auto_and_peatonal_variants(self) -> None:
        mod = _load_migration()
        first, second = mod.UPGRADE_STATEMENTS
        assert "LOWER(TRIM(transporte)) = 'auto'" in first
        assert "'vehicular'" in first
        assert "IN ('peaton', 'peatonal', 'walking')" in second


class TestSeedUsesCanonicalValues:
    def test_salida_norte_is_vehicular(self) -> None:
        norte = next(z for z in ZONES_DATA if z["name"] == "Salida Norte Auto")
        assert norte["transporte"] == "vehicular"

    def test_salida_sur_is_peatonal(self) -> None:
        sur = next(z for z in ZONES_DATA if z["name"] == "Salida Sur Peatonal")
        assert sur["transporte"] == "peatonal"

    def test_no_seed_zone_uses_legacy_auto(self) -> None:
        legacy = [z["name"] for z in ZONES_DATA if z.get("transporte") == "auto"]
        assert legacy == []


@pytest.fixture()
def pg_tx_conn():
    """Conexión con transacción propia sobre un schema temporal.

    El schema aísla las tablas scratch (sin geometry => no requiere PostGIS)
    del resto de la BD; el rollback final garantiza cero persistencia.
    """
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    conn = engine.connect()
    trans = conn.begin()
    conn.execute(text("DROP SCHEMA IF EXISTS tmp_norm_test CASCADE"))
    conn.execute(text("CREATE SCHEMA tmp_norm_test"))
    conn.execute(text("SET LOCAL search_path TO tmp_norm_test"))
    yield conn
    trans.rollback()
    conn.close()
    engine.dispose()


SCRATCH_DDL = """
CREATE TABLE events (id VARCHAR(36) PRIMARY KEY);
CREATE TABLE zones (
    id VARCHAR(36) PRIMARY KEY,
    event_id VARCHAR(36) REFERENCES events(id),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    transporte VARCHAR(50)
);
"""

# (type, transporte_original) -> esperado tras upgrade
UPGRADE_EXPECTATIONS = [
    ("salida", "auto", "vehicular"),          # caso producción real
    ("salida", "AUTO", "vehicular"),          # defensivo: mayúsculas
    ("salida", "  auto  ", "vehicular"),      # defensivo: espacios
    ("salida", "Auto", "vehicular"),          # defensivo: mixto
    ("salida", "peaton", "peatonal"),         # defensivo: variante
    ("salida", "walking", "peatonal"),        # defensivo: variante
    ("salida", "peatonal", "peatonal"),       # ya canónico: sin cambio
    ("salida", None, None),                   # NULL: sin cambio
    ("estacionamiento", "auto", "auto"),      # NO salida: intocada
    ("comida", "AUTO", "AUTO"),               # NO salida: intocada
    ("transporte", None, None),               # paradas: intocadas
]


def _seed_rows(conn):
    conn.execute(text("INSERT INTO events (id) VALUES ('ev-1')"))
    for i, (ztype, transporte, _) in enumerate(UPGRADE_EXPECTATIONS):
        conn.execute(
            text(
                "INSERT INTO zones (id, event_id, name, type, transporte) "
                "VALUES (:id, 'ev-1', :name, :type, :transporte)"
            ),
            {"id": f"z-{i:02d}", "name": f"Zona {i}", "type": ztype, "transporte": transporte},
        )


def _fetch_rows(conn):
    result = conn.execute(text(
        "SELECT type, transporte FROM zones ORDER BY id"
    ))
    return result.all()


def _run_statements(conn, statements):
    for stmt in statements:
        conn.exec_driver_sql(stmt)


def _expected_after_downgrade(ztype: str, original) -> object:
    """Semántica documentada: downgrade solo revierte 'vehicular'->'auto'.

    Las variantes de peatonal normalizadas permanecen canónicas y las filas
    no-salida jamás son tocadas por upgrade ni downgrade.
    """
    if ztype != "salida":
        return original
    if original is None:
        return None
    if original.strip().lower() == "auto":
        return "auto"
    return "peatonal"


class TestNormalizeSqlFunctional:
    """Ejecuta el SQL REAL de la migración contra un schema desechable."""

    def test_upgrade_normalize_idempotent_and_downgrade(self, pg_tx_conn) -> None:
        mod = _load_migration()
        conn = pg_tx_conn
        conn.exec_driver_sql(SCRATCH_DDL)
        _seed_rows(conn)

        # ── upgrade ──
        _run_statements(conn, mod.UPGRADE_STATEMENTS)
        rows = _fetch_rows(conn)
        for (ztype, original, expected), row in zip(UPGRADE_EXPECTATIONS, rows):
            assert (row[0], row[1]) == (ztype, expected), (
                f"fila type={ztype!r} original={original!r}: "
                f"esperado {expected!r}, obtenido {row[1]!r}"
            )

        # ── idempotencia: segundo upgrade no cambia nada ──
        snapshot = _fetch_rows(conn)
        _run_statements(conn, mod.UPGRADE_STATEMENTS)
        assert _fetch_rows(conn) == snapshot, "upgrade re-ejecutado alteró datos"

        # ── downgrade: vehicular -> auto; peatonal canónico permanece ──
        _run_statements(conn, mod.DOWNGRADE_STATEMENTS)
        rows_down = _fetch_rows(conn)
        for (ztype, original, _), row in zip(UPGRADE_EXPECTATIONS, rows_down):
            expected = _expected_after_downgrade(ztype, original)
            assert (row[0], row[1]) == (ztype, expected), (
                f"[downgrade] fila type={ztype!r} original={original!r}: "
                f"esperado {expected!r}, obtenido {row[1]!r}"
            )
