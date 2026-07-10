"""
Seed de migracion P3.0 — Backfill de EventDays y creacion de OperationalProfiles.

EJECUTAR ANTES de: alembic upgrade head
IDEMPOTENTE: puede ejecutarse multiples veces sin error.

Uso:
    export DATABASE_URL="postgresql://..."
    python scripts/seed_p3_migration.py
"""
import os

from sqlalchemy import create_engine, text

REFERENCE_PROFILES = [
    "ActividadExtendida",
    "AfluenciaTemprana",
    "AfluenciaTardía",
    "DoblePico",
    "PicoNocturno",
    "BajaActividadContinua",
]


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL no esta definida")

    engine = create_engine(database_url)

    with engine.begin() as conn:
        created = 0
        existing = 0

        for name in REFERENCE_PROFILES:
            row = conn.execute(
                text("SELECT COUNT(*) FROM operational_profiles WHERE name = :name"),
                {"name": name},
            ).scalar()

            if row == 0:
                conn.execute(
                    text("""
                        INSERT INTO operational_profiles (id, name, created_at, updated_at)
                        VALUES (gen_random_uuid(), :name, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """),
                    {"name": name},
                )
                created += 1
            else:
                existing += 1

        default_id = conn.execute(
            text("SELECT id FROM operational_profiles WHERE name = 'ActividadExtendida'"),
        ).scalar()

        if default_id:
            result = conn.execute(
                text("""
                    UPDATE event_days
                    SET operational_profile_id = :profile_id,
                        operational_start_min = 480,
                        operational_end_min = 1800
                    WHERE operational_profile_id IS NULL
                """),
                {"profile_id": default_id},
            )
            updated = result.rowcount
        else:
            updated = 0

    print(f"Perfiles creados: {created}")
    print(f"Perfiles ya existentes: {existing}")
    print(f"EventDays actualizados: {updated}")
    print("Seed de migracion completado. Seguro ejecutar alembic upgrade head.")


if __name__ == "__main__":
    main()
