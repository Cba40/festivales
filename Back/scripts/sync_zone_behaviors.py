"""
P3.1B — Comando administrativo para sincronizar ZoneBehavior sobre una base existente.

Idempotente: completa únicamente las combinaciones (phase, zone_type) faltantes,
sin modificar ni reemplazar los ZoneBehavior ya existentes.

NO se ejecuta automáticamente al iniciar la aplicación. Debe invocarse
explícitamente (mantenimiento / deploy):

    export DATABASE_URL="postgresql://..."
    python scripts/sync_zone_behaviors.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.zone_behavior_sync import sync_zone_behaviors


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL no está definida")

    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        created = sync_zone_behaviors(db)
        db.commit()
        print(f"Sincronización de ZoneBehavior completada. Creados: {created}")
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()
