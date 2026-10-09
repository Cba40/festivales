"""Restaura la base de prueba de Neon al estado que espera el ORM.

Necesario porque `tests/conftest.py::test_engine` hace
`DROP SCHEMA public CASCADE` sobre TEST_DATABASE_URL al iniciar y terminar la
sesion de tests. Los archivos de test que dependen de ese fixture borran la base.

Pasos: PostGIS -> las 3 cabezas de Alembic -> event_day_phases.intensity
(que ninguna migracion crea, aunque el ORM la declara NOT NULL).
"""
import subprocess
import sys

NEON = ("postgresql+psycopg://neondb_owner:npg_KpT6QkHf4dcz@"
        "ep-little-fire-b4xdm04n-pooler.c-6.us-east-2.aws.neon.tech/"
        "territorial_mvp_test?sslmode=require&channel_binding=require")
HEADS = ["a8b9c0d1e2f3", "b94a2f6cfa5b", "d2a4b6c8e0f1"]

import psycopg2

conn = psycopg2.connect(
    NEON.replace("postgresql+psycopg://", "postgresql://"), connect_timeout=30)
conn.autocommit = True
cur = conn.cursor()
cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
print("1/4 postgis ok")
conn.close()

for head in HEADS:
    r = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", head],
        capture_output=True, text=True,
        env={**__import__("os").environ, "DATABASE_URL": NEON},
    )
    print(f"2/4 alembic upgrade {head}: rc={r.returncode}")
    if r.returncode != 0:
        print(r.stderr[-800:])
        sys.exit(1)

conn = psycopg2.connect(
    NEON.replace("postgresql+psycopg://", "postgresql://"), connect_timeout=30)
conn.autocommit = True
cur = conn.cursor()
cur.execute("""ALTER TABLE event_day_phases
               ADD COLUMN IF NOT EXISTS intensity double precision NOT NULL DEFAULT 1.0;""")
print("3/4 event_day_phases.intensity ok")

cur.execute("""SELECT count(*) FROM information_schema.tables
               WHERE table_schema='public' AND table_type='BASE TABLE';""")
print("    tablas:", cur.fetchone()[0])
cur.execute("SELECT version_num FROM alembic_version;")
print("4/4 alembic_version:", cur.fetchall())
conn.close()
print("RESTAURADO")
