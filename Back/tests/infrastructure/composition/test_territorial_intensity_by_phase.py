"""Mide el efecto de las fases sobre la "intensidad territorial" de 39 zonas.

AVISO SOBRE LOS DATOS
---------------------
Las 39 zonas reales del "Festival de Jesús María 2026" NO son accesibles desde
este entorno: viven en la base del backend desplegado, sin credenciales. La base
de dev tiene 0 eventos y la de test no tiene la tabla `events`. Lo que sigue es
un escenario SINTETICO de 39 zonas con una mezcla de tipos plausible para un
festival. Las CIFRAS son reales (calculadas por el motor contra la BD) pero la
COMPOSICION es inventada. Sirve para medir el mecanismo, no para reportar el
estado del evento real.

Que mide
--------
1. Que `saturation_level` ahora se llene (via el mapeo desde `occupancy_ratio`).
2. Que cambie entre fases, porque `intensity` llega al modelo.
3. Cuanto se moveria el numero del `EventStatusBar` con la formula de "promedio
   de saturation_level", y por que esa formula es engañosa con la mezcla de
   tipos actual.
4. Cuantas zonas quedan DENTRO de ese promedio. Antes de conectar
   `service_configs.average_duration_min` eran 8 de 39 (solo estacionamientos);
   con los banos conectados son 17 de 39. El resto de tipos todavia no tiene
   modelo, y eso se imprime para que el numero no se lea como cobertura total.
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.attendance_level import AttendanceLevel
from app.models.event import Event
from app.models.event_day import EventDay
from app.models.event_day_phase import EventDayPhase
from app.models.motor_config import RecommendationConfigModel, Stage4ConfigModel
from app.models.operational_phase import OperationalPhase
from app.models.operational_profile import OperationalProfile
from app.models.service_config import ServiceConfig
from app.models.zone import Zone
from app.models.zone_behavior import ZoneBehavior
from app.models.zone_type import ZoneType
from src.infrastructure.composition.prediction_module import PredictionModule

LOCAL_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

EVENT_ID = "f0000000-0000-0000-0000-000000000001"
PROFILE_ID = "f0000000-0000-0000-0000-000000000002"
ATTENDANCE_ID = "f0000000-0000-0000-0000-000000000003"
EVENT_DAY_ID = "f0000000-0000-0000-0000-000000000004"
SC_BANOS_ID = "f0000000-0000-0000-0000-000000000501"

# 10 fases contiguas de 144 min. La intensidad es lo que el operador configura
# en "Fases de la jornada" y lo que RFC-007 §4.3 declara como la via por la que
# el evento expresa su comportamiento temporal.
INTENSIDADES = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.9, 1.0, 0.6]
FASE_1 = 0   # 00:00-02:24, intensity 0.1
FASE_9 = 8   # 19:12-21:36, intensity 1.0

# Mezcla de tipos de un festival. Solo `estacionamiento` y `servicios/banos`
# tienen modelo especializado (parking_v1 / bathroom_v1).
TIPOS = [
    ("estacionamiento", None, 8, 800),
    ("servicios", "banos", 9, 250),
    ("servicios", "hidratacion", 4, 120),
    ("comida", None, 8, 400),
    ("cionreo", None, 5, 900),
    ("descanso", None, 3, 150),
    ("escenario", None, 2, 3000),
]
TOTAL_ZONAS = sum(c for _t, _s, c, _cap in TIPOS)  # 39

# Zonas con modelo especializado: los estacionamientos (parking_v1) y los
# banos (bathroom_v1). Parking ya calculaba; los banos solo desde que
# `average_duration_min` llega al contexto desde `service_configs`.
ZONAS_MODELADAS = sum(
    c for t, s, c, _cap in TIPOS if t == "estacionamiento" or s == "banos"
)  # 17

# Permanencia de visita a un baño publico. En MINUTOS, como la columna.
DURACION_BANOS_MIN = 5


def _async_url(url: str) -> str:
    return re.sub(r"\bsslmode=([a-z]+)", r"ssl=\1", url)


@pytest.fixture(scope="module")
async def engine():
    url = os.environ.get("TEST_DATABASE_URL") or settings.DATABASE_URL
    eng = create_async_engine(_async_url(url), poolclass=NullPool)
    yield eng
    await eng.dispose()


async def _limpiar(conn) -> None:
    await conn.execute(sa.text("DELETE FROM service_configs WHERE id = :i"), {"i": SC_BANOS_ID})
    await conn.execute(sa.text("DELETE FROM zones WHERE event_id = :e"), {"e": EVENT_ID})
    await conn.execute(
        sa.text("DELETE FROM event_day_phases WHERE event_day_id = :d"), {"d": EVENT_DAY_ID}
    )
    await conn.execute(sa.text("DELETE FROM event_days WHERE id = :d"), {"d": EVENT_DAY_ID})
    await conn.execute(
        sa.text("DELETE FROM attendance_levels WHERE id = :a"), {"a": ATTENDANCE_ID}
    )
    await conn.execute(sa.text("DELETE FROM events WHERE id = :e"), {"e": EVENT_ID})
    await conn.execute(sa.text("DELETE FROM zone_behaviors WHERE id::text LIKE 'ff%'"))
    await conn.execute(
        sa.text("DELETE FROM operational_phases WHERE operational_profile_id = :p"),
        {"p": PROFILE_ID},
    )
    await conn.execute(
        sa.text("DELETE FROM operational_profiles WHERE id = :p"), {"p": PROFILE_ID}
    )
    await conn.execute(sa.text("DELETE FROM zone_types WHERE name LIKE 'ZZ %'"))
    await conn.execute(sa.text("DELETE FROM stage4_config WHERE id = 1"))
    await conn.execute(sa.text("DELETE FROM recommendation_config WHERE id = 1"))


@pytest.fixture(scope="module")
async def escenario39(engine, test_engine):
    from src.infrastructure.persistence.models.knowledge_model_version import (
        KnowledgeModelVersionModel,
    )

    factory = async_sessionmaker(engine, expire_on_commit=False)
    hoy = date.today()

    async with engine.begin() as conn:
        await conn.execute(
            sa.text("CREATE SEQUENCE IF NOT EXISTS km_version_number_seq")
        )
        await conn.run_sync(KnowledgeModelVersionModel.__table__.create, checkfirst=True)
        await _limpiar(conn)

    phase_ids = [f"f0000000-0000-0000-0000-0000000001{i:02d}" for i in range(10)]
    zt_ids: dict[str, str] = {}
    zonas = []

    async with factory() as db:
        db.add(RecommendationConfigModel(id=1))
        db.add(Stage4ConfigModel(id=1))
        db.add(OperationalProfile(id=PROFILE_ID, name="ZZ Festival"))
        db.add(
            Event(id=EVENT_ID, name="ZZ Festival Sintetico",
                  start_date=hoy, end_date=hoy)
        )
        db.add(
            AttendanceLevel(id=ATTENDANCE_ID, event_id=EVENT_ID, name="Alto",
                            min_people=1000, max_people=10000)
        )
        for i, (slug, _sub, _n, _cap) in enumerate(TIPOS):
            zt_ids[slug] = f"f0000000-0000-0000-0000-0000000002{i:02d}"
            db.add(ZoneType(id=zt_ids[slug], name=f"ZZ {slug}", slug=slug,
                            icon="x", description="sintetico", default_factors={}))
        for i, pid in enumerate(phase_ids):
            db.add(OperationalPhase(id=pid, name=f"ZZ Fase {i + 1}", sort_order=i + 1,
                                    operational_profile_id=PROFILE_ID))
        await db.flush()

        beh = 0
        for slug, zt in zt_ids.items():
            for pid in phase_ids:
                beh += 1
                db.add(ZoneBehavior(id=f"ff{beh:030d}", operational_phase_id=pid,
                                    zone_type_id=zt, density_factor=0.5,
                                    flow_restriction="OPEN"))
        db.add(
            EventDay(id=EVENT_DAY_ID, event_id=EVENT_ID, date=hoy, day_of_week="lunes",
                     operational_start_min=0, operational_end_min=1440,
                     attendance_level_id=ATTENDANCE_ID,
                     operational_profile_id=PROFILE_ID,
                     estimated_vehicles=1200, average_parking_duration=2.0)
        )
        for i, pid in enumerate(phase_ids):
            db.add(EventDayPhase(id=f"f0000000-0000-0000-0000-0000000003{i:02d}",
                                 event_day_id=EVENT_DAY_ID, operational_phase_id=pid,
                                 start_min=i * 144, end_min=(i + 1) * 144,
                                 intensity=INTENSIDADES[i]))
        await db.flush()

        n = 0
        for slug, sub, count, cap in TIPOS:
            for k in range(count):
                n += 1
                zonas.append(Zone(
                    id=f"f0000000-0000-0000-0000-0000000004{n:02d}",
                    event_id=EVENT_ID,
                    name=f"{slug}{'-' + sub if sub else ''} {k + 1}",
                    type=slug, subtipo=sub, capacity=cap + 50 * k,
                    latitude=-31.4 - n * 0.001, longitude=-64.18 - n * 0.001,
                ))
        assert len(zonas) == TOTAL_ZONAS, f"esperaba {TOTAL_ZONAS} zonas"
        db.add_all(zonas)
        await db.flush()

        # Lo que habilita el modelo de banos: sin esta fila,
        # `_resolve_service_durations_by_zone` no encuentra `average_duration_min`
        # y las 9 zonas de banos quedan fuera del indicador (8 de 39, no 17).
        # `event_day_id=NULL` es el default global; el override por jornada se
        # puede agregar despues sin tocar este.
        db.add(
            ServiceConfig(
                id=SC_BANOS_ID,
                zone_type_id=zt_ids["servicios"],
                subtipo="banos",
                event_day_id=None,
                average_duration_min=DURACION_BANOS_MIN,
                bathroom_use_rate_per_person_hour=0.1,
            )
        )
        await db.commit()

    yield {"hoy": hoy, "factory": factory, "phase_ids": phase_ids}

    async with engine.begin() as conn:
        await _limpiar(conn)


def _ts(hoy: date, fase: int) -> datetime:
    return datetime.combine(hoy, datetime.min.time(), tzinfo=LOCAL_TZ) + timedelta(
        minutes=fase * 144 + 72
    )


async def _pred(factory, hoy, fase):
    async with factory() as db:
        return await PredictionModule(db).execute(timestamp=_ts(hoy, fase), event_id=EVENT_ID)


def _statusbar_avg_saturation(states) -> tuple[int, int]:
    """La formula que propone el PASO 2: promedio de saturation_level x 100.

    Devuelve tambien cuantas zonas entraron en el promedio, porque con la mezcla
    de tipos actual el denominador NO son todas las zonas y eso hay que verlo.
    """
    con_dato = [z for z in states if z.saturation_level is not None]
    pct = round(sum(z.saturation_level for z in con_dato) / len(con_dato) * 100) if con_dato else 0
    return pct, len(con_dato)


async def test_medicion_de_intensidad_por_fase(escenario39):
    hoy, factory = escenario39["hoy"], escenario39["factory"]

    pred1 = await _pred(factory, hoy, FASE_1)   # intensity 0.1
    pred9 = await _pred(factory, hoy, FASE_9)   # intensity 1.0

    z1 = {z.zone_id: z for z in pred1.zone_states}
    z9 = {z.zone_id: z for z in pred9.zone_states}

    line = "=" * 108
    print(f"\n{line}")
    print(f"ESCENARIO SINTETICO: {len(pred1.zone_states)} zonas, 10 fases,(EventDayPhase.intensity)")
    print(f"  Fase 1 (min 0-144)   intensity={INTENSIDADES[FASE_1]}")
    print(f"  Fase 9 (min 1152-1296) intensity={INTENSIDADES[FASE_9]}")
    print(line)
    print(f"{'zona':<22}{'tipo':<20}{'proj_dens':>10}{'sat F1':>9}{'sat F9':>9}"
          f"{'estado F1':>14}{'estado F9':>14}")
    print(line)

    cambios = 0
    for zid in sorted(z1, key=lambda k: str(k)):
        a, b = z1[zid], z9[zid]
        sat1 = "—" if a.saturation_level is None else f"{a.saturation_level:.3f}"
        sat9 = "—" if b.saturation_level is None else f"{b.saturation_level:.3f}"
        if a.saturation_level is not None and b.saturation_level is not None \
                and abs(a.saturation_level - b.saturation_level) > 1e-9:
            cambios += 1
        etiqueta = f"{a.type}{'/' + str(a.subtipo) if a.subtipo else ''}"
        print(f"{str(a.zone_id)[-6:]:<22}{etiqueta:<20}{a.projected_density:>10}"
              f"{sat1:>9}{sat9:>9}{a.operational_state:>14}{b.operational_state:>14}")

    print(line)
    con_modelo = sum(1 for z in pred1.zone_states if z.saturation_level is not None)
    con_banos = sum(
        1 for z in pred1.zone_states
        if z.subtipo == "banos" and z.saturation_level is not None
    )
    print(f"zonas con saturation_level: {con_modelo}/{len(pred1.zone_states)}")
    print(f"  de las cuales banos: {con_banos}")
    print(f"zonas cuya saturacion CAMBIO entre fases: {cambios}")

    pct1, n1 = _statusbar_avg_saturation(pred1.zone_states)
    pct9, n9 = _statusbar_avg_saturation(pred9.zone_states)
    print(f"\nEventStatusBar con la formula 'promedio de saturation_level x 100':")
    print(f"  Fase 1 (0.1): {pct1}%   (calculado sobre {n1} de {len(pred1.zone_states)} zonas)")
    print(f"  Fase 9 (1.0): {pct9}%   (calculado sobre {n9} de {len(pred9.zone_states)} zonas)")
    print(line)
    print("\nCOBERTURA DEL INDICADOR (antes vs despues de conectar banos):")
    print(f"  antes:  8/39 zonas  = 21% del territorio dentro del promedio")
    print(f"  ahora: {con_modelo}/39 zonas = "
          f"{round(con_modelo / TOTAL_ZONAS * 100)}% del territorio dentro del promedio")
    print(f"  siguen sin modelo (fuera del promedio): "
          f"{TOTAL_ZONAS - con_modelo} zonas (hidratacion, comida, cionreo, descanso, escenario)")
    print(line + "\n")

    assert len(pred1.zone_states) == TOTAL_ZONAS
    assert con_modelo > 0, "el mapeo occupancy_ratio -> saturation_level no esta llenando nada"
    assert cambios > 0, "la intensidad de fase no movio ninguna zona"

    # El denominador del EventStatusBar. Estuvo en 8 (solo estacionamientos) y
    # subio a 17 al conectarse `average_duration_min`: 8 estacionamientos + 9
    # banos. Si esto baja, los banos volverian a degradar en silencio.
    assert con_modelo == ZONAS_MODELADAS, (
        f"esperaba {ZONAS_MODELADAS} zonas con saturacion "
        f"(8 estacionamientos + 9 banos) y hay {con_modelo}. "
        "Revisar la fila de service_configs para banos."
    )
    assert con_banos == 9, (
        f"los 9 banos deberian tener saturacion y hay {con_banos} con dato"
    )

    # El punto de todo el cambio: los banos tienen que RESPONDER a la fase, no
    # solo existir. Sin esto, 9 ceros en el promedio bajarian el indicador.
    sat_banos_f1 = [
        z.saturation_level for z in pred1.zone_states if z.subtipo == "banos"
    ]
    sat_banos_f9 = [
        z.saturation_level for z in pred9.zone_states if z.subtipo == "banos"
    ]
    assert all(v is not None for v in sat_banos_f1 + sat_banos_f9)
    assert sum(sat_banos_f9) > sum(sat_banos_f1), (
        f"la fase de mayor intensidad no subio la saturacion de los banos: "
        f"F1={sum(sat_banos_f1):.3f} vs F9={sum(sat_banos_f9):.3f}"
    )

    assert pct9 > pct1, (
        f"el porcentaje no subio en la fase de mayor intensidad: "
        f"F1={pct1}% vs F9={pct9}%"
    )
