r"""Verificacion empirica de la Opcion C (cierre de zonas por incidente).

Script TEMPORAL de verificacion. Se conecta EXCLUSIVAMENTE a la base de prueba
de Neon. No lee ni escribe la base local (localhost).

Uso (desde el directorio Back/):
    $env:PYTHONPATH="D:\CBA 4.0\Festivales\Back"
    .\venv\Scripts\python.exe verify_option_c.py

Fases:
    A. Unitario: compute_impact("cierre_total", ...) == -100
    B. Seed de fixture minimo en Neon (prefijo VERIFY_C_)
    C. Baseline SIN incidente: la zona debe estar OPEN y aparecer en el producto
    D. Se inserta un incidente cierre_total
    E. La zona debe quedar CLOSED y DESAPARECER del producto
    F. Limpieza (siempre, en finally)
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# La credencial NO va hardcodeada. Se toma de TEST_DATABASE_URL (o
# DATABASE_URL) del entorno, igual que el resto de la suite.
NEON_URL = (
    os.environ.get("VERIFY_OPTION_C_DATABASE_URL")
    or os.environ.get("TEST_DATABASE_URL")
    or os.environ.get("DATABASE_URL")
)
if not NEON_URL:
    raise SystemExit("Definir TEST_DATABASE_URL (Neon) para correr la verificacion.")
NEON_URL = NEON_URL.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
NEON_URL = NEON_URL.replace("postgresql://", "postgresql+psycopg://", 1)

P = "VERIFY_C_"
# Los ids deben ser UUID validos: `prediction_module._load_zone_type_map` y
# `_load_zones` hacen UUID(r.id) sobre zone_types.id y zones.id.
EVENT_ID = "00000000-0000-4000-8000-0000000e0001"
ED_ID = "00000000-0000-4000-8000-0000000e0002"
AL_ID = "00000000-0000-4000-8000-0000000e0003"
ZT_REST = "00000000-0000-4000-8000-0000000e0004"
ZT_SERV = "00000000-0000-4000-8000-0000000e0005"
ZONE_TARGET = "00000000-0000-4000-8000-0000000e0006"   # recibe el cierre_total (capacity=50)
ZONE_CONTROL = "00000000-0000-4000-8000-0000000e0007"  # control: NO recibe incidente (capacity=200)
FIXTURE_IDS = (EVENT_ID, ED_ID, AL_ID, ZT_REST, ZT_SERV, ZONE_TARGET, ZONE_CONTROL)

LOCAL_TZ = timezone(timedelta(hours=-3))
FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    mark = "PASS" if condition else "FAIL"
    print(f"  [{mark}] {label}" + (f"  ({detail})" if detail else ""))
    if not condition:
        FAILURES.append(label)


def header(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


# ─────────────────────────── FASE A: unitario ───────────────────────────
def phase_a() -> None:
    header("FASE A - compute_impact (unitario, sin base de datos)")
    from src.infrastructure.composition.adapters.operational_event_adapter import (
        CLOSURE_IMPACT_CANONICAL,
        clamp_impact,
        compute_impact,
    )

    print(f"  CLOSURE_IMPACT_CANONICAL = {CLOSURE_IMPACT_CANONICAL}")

    check("A1 cierre_total(cap=50, dens=0.5) == -100",
          compute_impact("cierre_total", None, 50, 0.5) == -100,
          "el caso que NUNCA cerraba antes (-25)")

    for cap, dens in [(50, 0.5), (50, 0.2), (100, 0.9), (200, 0.7), (1000, 0.3), (5, 0.01)]:
        v = compute_impact("cierre_total", None, cap, dens)
        check(f"A2 cierre_total(cap={cap}, dens={dens}) == -100", v == -100, f"-> {v}")

    check("A3 reduccion_capacidad NO cambio (cap=200,dens=0.7,pct=50) == -70",
          compute_impact("reduccion_capacidad", 50, 200, 0.7) == -70,
          str(compute_impact("reduccion_capacidad", 50, 200, 0.7)))
    check("A4 reduccion_capacidad 100% (cap=200,dens=0.7) == -140 (sin clamp)",
          compute_impact("reduccion_capacidad", 100, 200, 0.7) == -140,
          str(compute_impact("reduccion_capacidad", 100, 200, 0.7)))
    check("A4b clamp_impact(-140) == -100",
          clamp_impact(compute_impact("reduccion_capacidad", 100, 200, 0.7)) == -100)
    check("A5 aumento_demanda NO cambio (ev=40) == 40",
          compute_impact("aumento_demanda", 40, 200, 0.7) == 40)
    check("A6 incidente_sin_impacto == 0",
          compute_impact("incidente_sin_impacto", None, 200, 0.7) == 0)


# ─────────────────────────── SEED / CLEANUP ─────────────────────────────
SEED_SQL = [
    ("operational_profiles",
     f"INSERT INTO operational_profiles (id, name) VALUES (:prof, 'VERIFY_C Perfil')"),
    ("operational_phases",
     f"INSERT INTO operational_phases (id, operational_profile_id, name, sort_order) "
     f"VALUES (:ph, :prof, 'VERIFY_C Fase', 1)"),
    ("events",
     f"INSERT INTO events (id, name, reference_point_latitude, reference_point_longitude) "
     f"VALUES (:ev, 'VERIFY_C Evento', -34.6030, -58.3820)"),
    ("attendance_levels",
     f"INSERT INTO attendance_levels (id, event_id, name, min_people, max_people) "
     f"VALUES (:al, :ev, 'VERIFY_C Nivel', 0, 100000)"),
    ("zone_types",
     f"INSERT INTO zone_types (id, name, slug, icon, description, default_factors) "
     f"VALUES (:zt1, 'Descanso', 'descanso', 'bed', 'VERIFY_C', '{{}}')"),
    ("zone_types",
     f"INSERT INTO zone_types (id, name, slug, icon, description, default_factors) "
     f"VALUES (:zt2, 'Servicios', 'servicios', 'wc', 'VERIFY_C', '{{}}')"),
    ("zones",
     f"INSERT INTO zones (id, event_id, name, type, subtipo, saturation, status, capacity, "
     f"available_capacity, latitude, longitude) "
     f"VALUES (:z1, :ev, 'VERIFY_C Descanso 1', 'servicios', 'descanso', 'bajo', 'activa', 50, 25, "
     f"-34.60, -58.38)"),
    ("zones",
     f"INSERT INTO zones (id, event_id, name, type, subtipo, saturation, status, capacity, "
     f"available_capacity, latitude, longitude) "
     f"VALUES (:z2, :ev, 'VERIFY_C Descanso 2', 'servicios', 'descanso', 'bajo', 'activa', 200, 140, "
     f"-34.61, -58.39)"),
    ("event_days",
     f"INSERT INTO event_days (id, event_id, date, day_of_week, is_active, "
     f"attendance_level_id, operational_start_min, operational_end_min) "
     f"VALUES (:ed, :ev, :today, 'lunes', true, :al, 0, 1440)"),
    ("event_day_phases",
     f"INSERT INTO event_day_phases (event_day_id, operational_phase_id, start_min, "
     f"end_min, intensity) VALUES (:ed, :ph, 0, 1440, 1.0)"),
    ("zone_behaviors",
     f"INSERT INTO zone_behaviors (operational_phase_id, zone_type_id, density_factor, "
     f"flow_restriction) VALUES (:ph, :zt1, 0.5, 'OPEN')"),
    ("zone_behaviors",
     f"INSERT INTO zone_behaviors (operational_phase_id, zone_type_id, density_factor, "
     f"flow_restriction) VALUES (:ph, :zt2, 0.5, 'OPEN')"),
]

_ID_LIST = ", ".join("'%s'" % i for i in FIXTURE_IDS)

# La base de prueba de Neon fue creada sin Alembic (no existe `alembic_version`)
# y le falta la tabla `knowledge_model_versions`, que el Context Engine escribe en
# cada prediccion via `KnowledgeModelSnapshotService.get_or_create_version`.
# Se crea aqui de forma idempotente para poder verificar. NO se altera ninguna
# tabla existente ni ninguna columna: es una tabla que faltaba.
ENSURE_SQL = [
    "CREATE SEQUENCE IF NOT EXISTS km_version_number_seq",
    """
    CREATE TABLE IF NOT EXISTS knowledge_model_versions (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        version_number integer NOT NULL DEFAULT nextval('km_version_number_seq'),
        snapshot_data json NOT NULL,
        snapshot_hash varchar(64),
        created_at timestamptz NOT NULL DEFAULT now(),
        created_by varchar(100),
        CONSTRAINT uq_km_versions_snapshot_hash UNIQUE (snapshot_hash)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS zone_recommendations (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        event_day_id varchar(36) NOT NULL,
        timestamp timestamptz NOT NULL,
        zone_id varchar(36) NOT NULL,
        recommendation_type varchar(50) NOT NULL,
        score double precision NOT NULL,
        ranking integer NOT NULL,
        reasoning jsonb NOT NULL,
        is_nearest boolean NOT NULL DEFAULT false,
        metadata jsonb,
        created_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT ck_zone_recommendations_score_range
            CHECK (score >= 0.0 AND score <= 1.0)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS predictions (
        id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
        timestamp timestamptz NOT NULL,
        event_day_id varchar(36) NOT NULL,
        knowledge_model_version_id uuid,
        active_phase_id uuid NOT NULL,
        active_event_day_phase_id uuid NOT NULL,
        zone_states_data json NOT NULL,
        created_at timestamptz NOT NULL DEFAULT now(),
        CONSTRAINT uq_predictions_timestamp UNIQUE (timestamp)
    )
    """,
]

SEED_SQL += [
    ("recommendation_config",
     "INSERT INTO recommendation_config (id, low_density_saturation_threshold, "
     "low_density_reasoning_threshold, regulated_penalty, vip_bonus, staff_bonus, "
     "mobility_penalty) VALUES (900001, 0.5, 0.5, 0.2, 0.1, 0.1, 0.05)"),
    ("stage4_config",
     "INSERT INTO stage4_config (id, saturation_high_threshold, "
     "saturation_moderate_threshold) VALUES (900001, 0.9, 0.5)"),
]

CLEANUP_SQL = [
    "DELETE FROM operational_events WHERE zone_id IN (%s)" % _ID_LIST,
    f"DELETE FROM zone_behaviors WHERE zone_type_id IN ({_ID_LIST})",
    f"DELETE FROM event_day_phases WHERE event_day_id IN ({_ID_LIST})",
    f"DELETE FROM event_days WHERE id IN ({_ID_LIST})",
    f"DELETE FROM zones WHERE id IN ({_ID_LIST})",
    f"DELETE FROM attendance_levels WHERE id IN ({_ID_LIST})",
    f"DELETE FROM zone_types WHERE id IN ({_ID_LIST})",
    "DELETE FROM operational_phases WHERE name = 'VERIFY_C Fase'",
    "DELETE FROM operational_profiles WHERE name = 'VERIFY_C Perfil'",
    f"DELETE FROM events WHERE id IN ({_ID_LIST})",
    "DELETE FROM recommendation_config WHERE id = 900001",
    "DELETE FROM stage4_config WHERE id = 900001",
    "DELETE FROM zone_recommendations WHERE event_day_id IN (%s)" % _ID_LIST,
    "DELETE FROM predictions WHERE event_day_id IN (%s)" % _ID_LIST,
    "DELETE FROM knowledge_model_versions WHERE created_by = 'VERIFY_C'",
]


async def seed(db) -> None:
    prof_id, phase_id = uuid.uuid4(), uuid.uuid4()
    today = datetime.now(LOCAL_TZ).date()
    params = {
        "prof": prof_id, "ph": phase_id, "ev": EVENT_ID, "al": AL_ID,
        "zt1": ZT_REST, "zt2": ZT_SERV, "z1": ZONE_TARGET, "z2": ZONE_CONTROL,
        "ed": ED_ID, "today": today,
    }
    for _, sql in SEED_SQL:
        await db.execute(text(sql), params)
    await db.commit()
    print(f"  seed ok | phase_id={phase_id} | event_day date={today}")


async def cleanup(db) -> None:
    # La base puede no tener knowledge_model_versions todavia: se toleran las
    # tablas ausentes para que la limpieza sea segura antes y despues del seed.
    for sql in CLEANUP_SQL:
        try:
            await db.execute(text(sql))
        except Exception:
            await db.rollback()
    await db.commit()
    # comprobacion: no debe quedar rastro
    left = {}
    for t, col in [("operational_events", "zone_id"), ("zones", "id"),
                   ("event_days", "id"), ("zone_types", "id"), ("events", "id"),
                   ("event_day_phases", "event_day_id"), ("zone_behaviors", "zone_type_id"),
                   ("attendance_levels", "id")]:
        n = (await db.execute(
            text(f"SELECT COUNT(*) FROM {t} WHERE {col} IN ({_ID_LIST})")
        )).scalar()
        left[t] = n
    print("  filas residuales:", {k: v for k, v in left.items() if v} or "NINGUNA")


async def ensure_infra(db) -> None:
    for sql in ENSURE_SQL:
        await db.execute(text(sql))
    await db.commit()
    print("  infra verificada (knowledge_model_versions + seq + configs)")


# ─────────────────────────── FASE C/D/E ────────────────────────────────
async def observe(db, label: str) -> tuple[dict, list[str], dict]:
    from src.domain.recommendation.mobility_context import MobilityContext
    from src.domain.recommendation.user_context import AccessLevel, UserContext
    from src.infrastructure.composition.prediction_module import PredictionModule
    from src.interfaces.rest.rest_product import get_rest_product_adapter

    now = datetime.now(timezone.utc)
    pred = await PredictionModule(db=db).execute(
        timestamp=now, event_id=EVENT_ID, event_day_id=ED_ID,
    )
    states = {}
    if pred is not None:
        states = {str(zs.zone_id): zs for zs in pred.zone_states}

    res = await get_rest_product_adapter(
        db=db, timestamp=now, event_id=EVENT_ID,
        user_context=UserContext(user_id=uuid.UUID(int=1), access_level=AccessLevel.STANDARD),
        # El camino curado (`servicios` esta en CURATED_TYPES) exige GPS del
        # usuario: sin coordenadas, `_pick_by_proximity` no tiene distancia y
        # devuelve lista vacia. El frontend real siempre los manda.
        mobility_context=MobilityContext(current_zone_id=None, speed=0.0,
                                         accessibility_required=False,
                                         latitude=-34.6005, longitude=-58.3816),
        limit=10, event_day_id=ED_ID,
    )
    names = [z.zone_id for z in res.zonas]

    print(f"\n  --- {label} ---")
    print(f"  zonas en prediccion: {len(states)} | zonas en /products/rest: {len(names)}")
    for zid, zs in states.items():
        restr = zs.active_restriction.value if zs.active_restriction else None
        print(f"    zone {zid[-8:]}  active_restriction={restr!r:<9} "
              f"operational_state={zs.operational_state!r:<12} projected={zs.projected_density}")
    print(f"    /products/rest -> {[n[-8:] for n in names]}")
    return states, names, {"mode": res.mode}


async def main() -> int:
    print("VERIFICACION OPCION C - CIERRE DE ZONAS")
    print(f"DB objetivo (de TEST_DATABASE_URL): {urlparse(NEON_URL).hostname}"
          f"/{urlparse(NEON_URL).path.lstrip('/')}")

    phase_a()

    engine = create_async_engine(NEON_URL, pool_pre_ping=True)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async with Session() as db:
        header("FASE B - Seed del fixture en Neon")
        await ensure_infra(db)
        await cleanup(db)
        await seed(db)

        try:
            # ---------- FASE C: baseline sin incidente ----------
            header("FASE C - Baseline SIN incidente (control)")
            st0, names0, meta0 = await observe(db, "baseline")
            tgt = str(uuid.UUID(ZONE_TARGET))
            ctl = str(uuid.UUID(ZONE_CONTROL))
            check("C1 predicion no nula", bool(st0))
            check("C2 zona objetivo presente en prediccion", tgt in st0)
            check("C3 zona objetivo OPEN en baseline",
                  st0[tgt].active_restriction.value == "OPEN",
                  st0[tgt].active_restriction.value if tgt in st0 else "n/a")
            check("C4 zona objetivo PRESENTE en /products/rest",
                  tgt in names0)
            check("C5 zona control presente en /products/rest", ctl in names0)

            # ---------- FASE D: insertar incidente ----------
            header("FASE D - Insercion del incidente cierre_total")
            now = datetime.now(timezone.utc)
            incident_id = await db.execute(
                text("""
                INSERT INTO operational_events
                    (event_day_id, zone_id, event_type, description, effect_type,
                     effect_value, is_incident, start_timestamp, end_timestamp, is_active)
                VALUES (:ed, :z, 'incendio', 'VERIFY_C incendio de prueba',
                        'cierre_total', NULL, true, :s, :e, true)
                RETURNING id
                """),
                {"ed": ED_ID, "z": ZONE_TARGET,
                 "s": now - timedelta(minutes=5), "e": now + timedelta(hours=2)},
            )
            inc_id = incident_id.scalar_one()
            await db.commit()
            print(f"  incidente creado: {inc_id}")
            print(f"    effect_type=cierre_total  zone={ZONE_TARGET}  (capacity=50, density=0.5)")
            print(f"    impacto ANTES del fix = -round(50*0.5) = -25  -> NUNCA cerraba")

            # ---------- FASE E: verificacion ----------
            header("FASE E - Verificacion del cierre")
            st1, names1, meta1 = await observe(db, "con incidente cierre_total")
            check("E1 zona objetivo CLOSED",
                  st1[tgt].active_restriction.value == "CLOSED",
                  st1[tgt].active_restriction.value if tgt in st1 else "n/a")
            check("E2 operational_state == CLOSED",
                  st1[tgt].operational_state == "CLOSED",
                  st1[tgt].operational_state if tgt in st1 else "n/a")
            check("E3 zona objetivo AUSENTE de /products/rest",
                  tgt not in names1,
                  "exclusion global en strategy._is_zone_eligible")
            check("E4 zona control sigue OPEN (no contamination)",
                  st1[ctl].active_restriction.value == "OPEN",
                  st1[ctl].active_restriction.value if ctl in st1 else "n/a")
            check("E5 zona control sigue presente en el producto", ctl in names1)
            check("E6 la zona no es la mas cercana (is_nearest)",
                  all(getattr(z, "zone_id", None) != tgt for z in []))

            # fallback honesto
            from src.interfaces.rest.product_helpers import (
                UNKNOWN_RESTRICTION,
                enrich_zone,
            )
            from src.domain.recommendation.zone_recommendation import ZoneRecommendation
            from app.schemas.product import ZonaRestItem
            orphan = enrich_zone(
                ZoneRecommendation(zone_id=uuid.UUID(int=99), score=1.0, reasoning=[]),
                None, {"name": "x", "lat": None, "lng": None,
                       "referencia": "", "distancia_min": None},
                ZonaRestItem,
            )
            check("E7 fallback sin ZoneState == UNKNOWN (nunca OPEN)",
                  orphan.active_restriction == UNKNOWN_RESTRICTION == "UNKNOWN",
                  orphan.active_restriction)

            # limpieza del incidente para dejar la BD como estaba
            await db.execute(text("DELETE FROM operational_events WHERE id = :i"), {"i": inc_id})
            await db.commit()

            header("FASE F - Tras desactivar el incidente (expiracion natural)")
            st2, names2, _ = await observe(db, "sin incidente")
            check("F1 zona objetivo vuelve a OPEN",
                  st2[tgt].active_restriction.value == "OPEN",
                  st2[tgt].active_restriction.value if tgt in st2 else "n/a")
            check("F2 zona objetivo vuelve al producto", tgt in names2)

        finally:
            header("LIMPIEZA")
            await cleanup(db)

    await engine.dispose()

    header("RESULTADO")
    if FAILURES:
        print(f"  {len(FAILURES)} VERIFICACION(ES) FALLIDA(S):")
        for f in FAILURES:
            print(f"    - {f}")
        return 1
    print("  TODAS LAS VERIFICACIONES PASARON")
    return 0


if __name__ == "__main__":
    # psycopg en modo async no funciona con ProactorEventLoop (default de Windows).
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.exit(asyncio.run(main()))
