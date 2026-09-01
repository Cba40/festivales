"""
Seed de referencia P3.0 — OperationalPhases y ZoneBehaviors.

EJECUTAR DESPUÉS de: alembic upgrade head + seed_p3_migration.py
IDEMPOTENTE: puede ejecutarse múltiples veces sin error ni duplicados.

Uso:
    export DATABASE_URL="postgresql://..."
    python scripts/seed_p3_reference_data.py
"""
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# ═══════════════════════════════════════════════════════════════
# DEFINICIÓN DE FASES POR PERFIL
# ═══════════════════════════════════════════════════════════════
# §11 de P3.0_EXECUTION_SPEC.md especifica solo ActividadExtendida.
# Los demás perfiles se derivan coherentemente según su nombre y patrón operativo.
# ───────────────────────────────────────────────────────────
# Cada tupla:  (name, sort_order)
# ───────────────────────────────────────────────────────────

PHASES_BY_PROFILE: dict[str, list[tuple[str, int]]] = {
    "ActividadExtendida": [
        ("Preparación", 1),
        ("ActividadComercial", 2),
        ("LlegadaVisitantes", 3),
        ("AltaActividad", 4),
        ("EspectáculoEnDesarrollo", 5),
        ("Dispersión", 6),
        ("CierreTerritorial", 7),
    ],
    "AfluenciaTemprana": [
        ("Preparación", 1),
        ("Apertura", 2),
        ("PicoMatutino", 3),
        ("ActividadContinua", 4),
        ("Dispersión", 5),
        ("CierreTerritorial", 6),
    ],
    "AfluenciaTardía": [
        ("Preparación", 1),
        ("ActividadPrevia", 2),
        ("LlegadaVisitantes", 3),
        ("AltaActividad", 4),
        ("Dispersión", 5),
        ("CierreTerritorial", 6),
    ],
    "DoblePico": [
        ("Preparación", 1),
        ("PrimerPico", 2),
        ("ActividadMedia", 3),
        ("SegundoPico", 4),
        ("Dispersión", 5),
        ("CierreTerritorial", 6),
    ],
    "PicoNocturno": [
        ("Preparación", 1),
        ("ActividadVespertina", 2),
        ("PicoNocturno", 3),
        ("AltaActividadNocturna", 4),
        ("Dispersión", 5),
        ("CierreTerritorial", 6),
    ],
    "BajaActividadContinua": [
        ("Preparación", 1),
        ("ActividadContinua", 2),
        ("ActividadTranquila", 3),
        ("Dispersión", 4),
        ("CierreTerritorial", 5),
    ],
}

# ═══════════════════════════════════════════════════════════════
# FACTORES DE ZoneBehavior PARA FASE "Dispersión" (§11)
# ═══════════════════════════════════════════════════════════════
# Mapeo por slug de ZoneType.
# Los slugs deben coincidir con los existentes en la tabla zone_types.
# ───────────────────────────────────────────────────────────

DISPERSION_FACTORS: dict[str, tuple[float, float, float, float]] = {
    "estacionamiento": (0.2, 3.0, 0.5, 0.3),
    "gastronomia": (2.5, 0.4, 2.0, 0.9),
    "transporte": (3.0, 0.3, 2.5, 1.0),
    "sanitarios": (2.0, 0.5, 1.5, 0.8),
    "seguridad": (1.5, 0.7, 1.8, 0.9),
}


# ═══════════════════════════════════════════════════════════════

async def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL no está definida")

    async_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(async_url)

    stats = {
        "phases_created": 0,
        "phases_existing": 0,
        "behaviors_created": 0,
        "behaviors_existing": 0,
    }

    async with engine.begin() as conn:
        # ── PASO 1: Obtener perfiles existentes ──────────────
        profile_rows = await conn.execute(
            text("SELECT id, name FROM operational_profiles"),
        )
        profiles: dict[str, str] = {row.name: row.id for row in profile_rows}

        missing = set(PHASES_BY_PROFILE) - set(profiles)
        if missing:
            raise RuntimeError(
                f"Perfiles faltantes en BD (ejecute seed_p3_migration.py primero): {missing}"
            )

        # ── PASO 2: Obtener ZoneTypes existentes ─────────────
        zt_rows = await conn.execute(
            text("SELECT id, slug FROM zone_types"),
        )
        zone_types_by_slug: dict[str, str] = {row.slug: row.id for row in zt_rows}

        if not zone_types_by_slug:
            raise RuntimeError("No hay ZoneTypes en la BD. Ejecute seed de zone_types primero.")

        # ── PASO 3: Insertar OperationalPhases ───────────────
        for profile_name, phases in PHASES_BY_PROFILE.items():
            profile_id = profiles[profile_name]

            for name, sort_order in phases:
                result = await conn.execute(
                    text("""
                        INSERT INTO operational_phases
                            (id, operational_profile_id, name,
                             sort_order, created_at, updated_at)
                        SELECT
                            gen_random_uuid(), :profile_id, :name,
                            :sort_order, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        WHERE NOT EXISTS (
                            SELECT 1 FROM operational_phases
                            WHERE operational_profile_id = :profile_id
                              AND sort_order = :sort_order
                        )
                    """),
                    {
                        "profile_id": profile_id,
                        "name": name,
                        "sort_order": sort_order,
                    },
                )
                count = result.rowcount
                if count:
                    stats["phases_created"] += count
                else:
                    stats["phases_existing"] += 1

        # ── PASO 4: Insertar ZoneBehaviors ───────────────────
        phase_rows = await conn.execute(
            text("""
                SELECT op.id, op.sort_order, pr.name AS profile_name
                FROM operational_phases op
                JOIN operational_profiles pr ON pr.id = op.operational_profile_id
            """),
        )
        phase_map: list[dict] = [
            {"id": row.id, "sort_order": row.sort_order, "profile_name": row.profile_name}
            for row in phase_rows
        ]

        default_factors = (1.0, 1.0, 1.0, 1.0)

        for phase in phase_map:
            phase_id = phase["id"]
            phase_sort_order = phase["sort_order"]
            profile_name = phase["profile_name"]

            profile_phases = PHASES_BY_PROFILE.get(profile_name, [])
            phase_def = next(
                (p for p in profile_phases if p[1] == phase_sort_order), None
            )
            phase_name = phase_def[0] if phase_def else ""

            # La fase "Dispersión" tiene factores específicos en §11
            is_dispersion = (phase_name == "Dispersión")

            for slug, zt_id in zone_types_by_slug.items():
                if is_dispersion and slug in DISPERSION_FACTORS:
                    sat, avail, res, prio = DISPERSION_FACTORS[slug]
                else:
                    sat, avail, res, prio = default_factors

                result = await conn.execute(
                    text("""
                        INSERT INTO zone_behaviors
                            (id, operational_phase_id, zone_type_id,
                             saturation_factor, availability_factor,
                             resource_factor, priority_weight,
                             created_at, updated_at)
                        SELECT
                            gen_random_uuid(), :phase_id, :zone_type_id,
                            :saturation_factor, :availability_factor,
                            :resource_factor, :priority_weight,
                            CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        WHERE NOT EXISTS (
                            SELECT 1 FROM zone_behaviors
                            WHERE operational_phase_id = :phase_id
                              AND zone_type_id = :zone_type_id
                        )
                    """),
                    {
                        "phase_id": phase_id,
                        "zone_type_id": zt_id,
                        "saturation_factor": sat,
                        "availability_factor": avail,
                        "resource_factor": res,
                        "priority_weight": prio,
                    },
                )
                count = result.rowcount
                if count:
                    stats["behaviors_created"] += count
                else:
                    stats["behaviors_existing"] += 1

    await engine.dispose()

    print(f"Fases creadas: {stats['phases_created']}")
    print(f"Fases ya existentes: {stats['phases_existing']}")
    print(f"Comportamientos creados: {stats['behaviors_created']}")
    print(f"Comportamientos ya existentes: {stats['behaviors_existing']}")
    print("✅ Seed de referencia completado.")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
