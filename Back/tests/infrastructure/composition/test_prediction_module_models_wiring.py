"""PASO 1 en la BD de test: los modelos especializados, de verdad.

Qué prueba
----------
Que `_build_model_selector()` conecte ParkingV1 y BathroomV1 al Context Engine y
que el endpoint público `/predictions` siga funcionando cuando un modelo NO puede
calcular. Sin la BD real esto no se puede verificar: los modelos dependen de
`event_days.estimated_vehicles` y de `attendance_level.max_people`, que son
NULLABLE, y el camino de degradación solo se ejercita si de verdad faltan.

Contra qué base
---------------
`TEST_DATABASE_URL` (la que el harness de `tests/conftest.py` usa, y cuyo nombre
termina en `_test`). NUNCA `settings.DATABASE_URL`.

Por qué un async engine propio y no el `db_session` de conftest
-------------------------------------------------------------
`db_session` abre una transacción que se revierte al final del test. El
`PredictionModule` necesita un `AsyncSession`, que va por otra conexión y por lo
tanto no vería datos sin commitear. Acá se commitea y se borra explícitamente.

Por qué el escenario se arma con los modelos ORM y no con SQL crudo
------------------------------------------------------------------
Un `INSERT` a mano depende de acertar los nombres de columna, y `zone_types` no
tiene `color` (tiene `icon`): el SQL crudo falla con `UndefinedColumnError` y
ese error se confunde con "la tabla no existe". Con los ORM, el esquema lo
garantiza el metadata y una columna mal escrita es un error de Python en el
test, no una SQLException.
"""
from __future__ import annotations

import os
import re
from datetime import date, datetime, timedelta
from uuid import UUID
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
from app.models.zone import Zone
from app.models.zone_behavior import ZoneBehavior
from app.models.zone_type import ZoneType
from src.infrastructure.composition.prediction_module import PredictionModule

LOCAL_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

EVENT_ID = "aaaaaaaa-0000-0000-0000-000000000001"
PROFILE_ID = "aaaaaaaa-0000-0000-0000-000000000002"
PHASE_BAJA = "aaaaaaaa-0000-0000-0000-000000000003"
PHASE_ALTA = "aaaaaaaa-0000-0000-0000-000000000004"
ATTENDANCE_ID = "aaaaaaaa-0000-0000-0000-000000000005"
ZONE_PARKING = "aaaaaaaa-0000-0000-0000-000000000006"
ZONE_BANOS = "aaaaaaaa-0000-0000-0000-000000000007"
ZONE_COMIDA = "aaaaaaaa-0000-0000-0000-000000000008"

EVENT_DAY_ID = "bbbbbbbb-0000-0000-0000-000000000001"

ZT_PARKING = "cccccccc-0000-0000-0000-000000000001"
ZT_SERVICIOS = "cccccccc-0000-0000-0000-000000000002"
ZT_COMIDA = "cccccccc-0000-0000-0000-000000000003"


def _async_url(url: str) -> str:
    """asyncpg no entiende `sslmode=require` (eso es de libpq).

    `TEST_DATABASE_URL` es una URL de Neon con `?sslmode=require`, pensada para
    psycopg. asyncpg quiere `?ssl=require`. Sin esta conversion el connect()
    falla con "connect() got an unexpected keyword argument 'sslmode'".
    """
    return re.sub(r"\bsslmode=([a-z]+)", r"ssl=\1", url)


async def _ensure_knowledge_model_versions(conn) -> None:
    """Crea `knowledge_model_versions` si no existe.

    `KnowledgeModelSnapshotService.get_or_create_version` la escribe en CADA
    prediccion, y es una de las 7 tablas que NO estan en
    `app.db.session.Base.metadata` (por eso `create_all` de conftest no la
    hace: la crea la migracion `p91_add_snapshot_hash_to_km_versions`). Sin esta
    fila/tabla, `PredictionModule.execute` revienta con
    `UndefinedTableError: relation "knowledge_model_versions" does not exist`
    antes de llegar al Context Engine.
    """
    from src.infrastructure.persistence.models.knowledge_model_version import (
        KnowledgeModelVersionModel,
    )

    # `version_number` usa la secuencia `km_version_number_seq`, que
    # `Table.create()` no emite (solo crea la tabla). Sin ella, el INSERT del
    # snapshot revienta con `relation "km_version_number_seq" does not exist`.
    await conn.execute(sa.text("CREATE SEQUENCE IF NOT EXISTS km_version_number_seq"))
    await conn.run_sync(
        KnowledgeModelVersionModel.__table__.create, checkfirst=True
    )


@pytest.fixture(scope="module")
async def engine():
    url = os.environ.get("TEST_DATABASE_URL") or settings.DATABASE_URL
    eng = create_async_engine(_async_url(url), poolclass=NullPool)
    yield eng
    await eng.dispose()


@pytest.fixture(scope="module")
async def escenario(engine, test_engine):
    """Crea el evento de prueba completo y lo borra al terminar.

    Depende de `test_engine` (session-scoped, de conftest) UNICAMENTE para que
    el schema exista: ese fixture hace `DROP SCHEMA public CASCADE` +
    `create_all` + siembra RBAC contra `TEST_DATABASE_URL`. Sin pedirlo, las
    tablas no estan creadas y el primer INSERT falla con `relation ... does not
    exist`. No se usa su sesion: esta prueba necesita `AsyncSession`, y el
    `db_session` de conftest vive en una transaccion que se revierte en otra
    conexion (y otra conexion no ve lo no commiteado).

    Dos fases con intensidades muy distintas (0.1 y 1.0) porque lo que se quiere
    demostrar es que la intensidad mueve el resultado del modelo.
    """
    hoy = date.today()
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await _ensure_knowledge_model_versions(conn)

    # Pre-limpieza. Si una corrida anterior fallo en el setup, su teardown nunca
    # corrio y dejo filas con estos mismo ids; sin esto el INSERT de abajo
    # revienta por PK duplicada y el fallo se propaga como si fuera del test.
    async with engine.begin() as conn:
        await conn.execute(sa.text("DELETE FROM zones WHERE event_id = :e"), {"e": EVENT_ID})
        await conn.execute(
            sa.text("DELETE FROM event_day_phases WHERE event_day_id = :d"), {"d": EVENT_DAY_ID}
        )
        # event_days ANTES que attendance_levels: `event_days.attendance_level_id`
        # es FK. Al reves es ForeignKeyViolationError en el teardown.
        await conn.execute(sa.text("DELETE FROM event_days WHERE id = :d"), {"d": EVENT_DAY_ID})
        await conn.execute(
            sa.text("DELETE FROM attendance_levels WHERE id = :a"), {"a": ATTENDANCE_ID}
        )
        await conn.execute(sa.text("DELETE FROM events WHERE id = :e"), {"e": EVENT_ID})
        await conn.execute(
            sa.text("DELETE FROM zone_behaviors WHERE id::text LIKE 'eeeeeeee-%'")
        )
        await conn.execute(
            sa.text("DELETE FROM operational_phases WHERE id IN (:a, :b)"),
            {"a": PHASE_BAJA, "b": PHASE_ALTA},
        )
        await conn.execute(
            sa.text("DELETE FROM operational_profiles WHERE id = :p"), {"p": PROFILE_ID}
        )
        await conn.execute(
            sa.text("DELETE FROM zone_types WHERE id IN (:a, :b, :c)"),
            {"a": ZT_PARKING, "b": ZT_SERVICIOS, "c": ZT_COMIDA},
        )
        await conn.execute(sa.text("DELETE FROM recommendation_config WHERE id = 1"))
        await conn.execute(sa.text("DELETE FROM stage4_config WHERE id = 1"))

    async with factory() as db:
        # `KnowledgeModelSnapshotService.capture_current_snapshot` (que corre en
        # CADA predicción) levanta `ValueError("recommendation_config is not
        # configured")` si la tabla no tiene fila. Es un requisito del flow, no
        # un detalle del test.
        db.add(RecommendationConfigModel(id=1))
        # Mismo motivo: `capture_current_snapshot` tambien exige
        # `stage4_config` (snapshot_service.py:40). Sin la fila, TODA
        # prediccion revienta antes de llegar al Context Engine.
        db.add(Stage4ConfigModel(id=1))
        db.add_all(
            [
                # `zone_types` exige NOT NULL en name, slug, icon, description y
                # default_factors. Omitir cualquiera de los cinco da
                # NotNullViolationError, no una columna opcional.
                ZoneType(
                    id=ZT_PARKING, name="Estacionamiento", slug="estacionamiento",
                    icon="car", description="Estacionamientos", default_factors={},
                ),
                ZoneType(
                    id=ZT_SERVICIOS, name="Servicios", slug="servicios",
                    icon="water", description="Servicios", default_factors={},
                ),
                ZoneType(
                    id=ZT_COMIDA, name="Comida", slug="comida",
                    icon="utensils", description="Comida", default_factors={},
                ),
                OperationalProfile(id=PROFILE_ID, name="P1 Test"),
                OperationalPhase(
                    id=PHASE_BAJA, name="Apertura", sort_order=1,
                    operational_profile_id=PROFILE_ID,
                ),
                OperationalPhase(
                    id=PHASE_ALTA, name="Clausura", sort_order=2,
                    operational_profile_id=PROFILE_ID,
                ),
            ]
        )
        await db.flush()
        # Id derivado de un contador, no de recortar strings: `phase[-12:]` daba
        # un UUID de 26 caracteres y asyncpg lo rechaza con DataError.
        beh_i = 0
        for zt in (ZT_PARKING, ZT_SERVICIOS, ZT_COMIDA):
            for phase in (PHASE_BAJA, PHASE_ALTA):
                beh_i += 1
                db.add(
                    ZoneBehavior(
                        id=f"eeeeeeee-0000-0000-0000-{beh_i:012d}",
                        operational_phase_id=phase,
                        zone_type_id=zt,
                        density_factor=0.5,
                        flow_restriction="OPEN",
                    )
                )
        db.add_all(
            [
                AttendanceLevel(
                    id=ATTENDANCE_ID, event_id=EVENT_ID,
                    name="Alto", min_people=100, max_people=5000,
                ),
                Event(id=EVENT_ID, name="P1 Test", start_date=hoy, end_date=hoy),
            ]
        )
        await db.flush()
        db.add(
            EventDay(
                id=EVENT_DAY_ID,
                event_id=EVENT_ID,
                date=hoy,
                day_of_week="lunes",
                operational_start_min=0,
                operational_end_min=1440,
                attendance_level_id=ATTENDANCE_ID,
                operational_profile_id=PROFILE_ID,
                estimated_vehicles=200,
                average_parking_duration=2.0,
            )
        )
        db.add_all(
            [
                EventDayPhase(
                    id="dddddddd-0000-0000-0000-000000000001",
                    event_day_id=EVENT_DAY_ID,
                    operational_phase_id=PHASE_BAJA,
                    start_min=0,
                    end_min=720,
                    intensity=0.1,
                ),
                EventDayPhase(
                    id="dddddddd-0000-0000-0000-000000000002",
                    event_day_id=EVENT_DAY_ID,
                    operational_phase_id=PHASE_ALTA,
                    # Contigua con la anterior, sin hueco: `resolve_contextual_phase`
                    # no tolera huecos y levanta `InvalidPhaseContext`
                    # ("No EventDayPhase contains minute N"). Con un hueco, el
                    # test falla por el escenario y no por lo que mide.
                    start_min=720,
                    end_min=1440,
                    intensity=1.0,
                ),
            ]
        )
        db.add_all(
            [
                Zone(
                    id=ZONE_PARKING, event_id=EVENT_ID, name="Parking",
                    type="estacionamiento", capacity=1000,
                    latitude=-31.41, longitude=-64.18,
                ),
                Zone(
                    id=ZONE_BANOS, event_id=EVENT_ID, name="Banos",
                    type="servicios", subtipo="banos", capacity=200,
                    latitude=-31.42, longitude=-64.19,
                ),
                Zone(
                    id=ZONE_COMIDA, event_id=EVENT_ID, name="Comida",
                    type="comida", capacity=500,
                    latitude=-31.43, longitude=-64.17,
                ),
            ]
        )
        await db.commit()

    yield {"hoy": hoy, "factory": factory}

    async with engine.begin() as conn:
        await conn.execute(sa.text("DELETE FROM zones WHERE event_id = :e"), {"e": EVENT_ID})
        await conn.execute(
            sa.text("DELETE FROM event_day_phases WHERE event_day_id = :d"), {"d": EVENT_DAY_ID}
        )
        # event_days ANTES que attendance_levels: `event_days.attendance_level_id`
        # es FK. Al reves es ForeignKeyViolationError en el teardown.
        await conn.execute(sa.text("DELETE FROM event_days WHERE id = :d"), {"d": EVENT_DAY_ID})
        await conn.execute(
            sa.text("DELETE FROM attendance_levels WHERE id = :a"), {"a": ATTENDANCE_ID}
        )
        await conn.execute(sa.text("DELETE FROM events WHERE id = :e"), {"e": EVENT_ID})
        await conn.execute(
            sa.text("DELETE FROM zone_behaviors WHERE id::text LIKE 'eeeeeeee-%'")
        )
        await conn.execute(
            sa.text("DELETE FROM operational_phases WHERE id IN (:a, :b)"),
            {"a": PHASE_BAJA, "b": PHASE_ALTA},
        )
        await conn.execute(
            sa.text("DELETE FROM operational_profiles WHERE id = :p"), {"p": PROFILE_ID}
        )
        await conn.execute(
            sa.text("DELETE FROM zone_types WHERE id IN (:a, :b, :c)"),
            {"a": ZT_PARKING, "b": ZT_SERVICIOS, "c": ZT_COMIDA},
        )
        await conn.execute(sa.text("DELETE FROM recommendation_config WHERE id = 1"))
        await conn.execute(sa.text("DELETE FROM stage4_config WHERE id = 1"))


def _ts(hoy: date, hora: int) -> datetime:
    return datetime.combine(hoy, datetime.min.time(), tzinfo=LOCAL_TZ) + timedelta(hours=hora)


async def _pred(factory, hoy: date, hora: int):
    async with factory() as db:
        return await PredictionModule(db).execute(timestamp=_ts(hoy, hora), event_id=EVENT_ID)


def _by_zone(pred) -> dict:
    return {str(z.zone_id): z for z in pred.zone_states}


class TestModelosConectados:
    async def test_no_revienta_y_devuelve_las_3_zonas(self, escenario):
        pred = await _pred(escenario["factory"], escenario["hoy"], 12)
        assert pred is not None
        assert len(pred.zone_states) == 3

    async def test_parking_recibe_modelo_parking(self, escenario):
        pred = await _pred(escenario["factory"], escenario["hoy"], 12)
        parking = _by_zone(pred)[ZONE_PARKING]
        assert parking.model_result is not None, (
            "el parking no recibio resultado del modelo: los modelos siguen sin "
            "conectarse al Context Engine"
        )
        assert parking.model_result["parking_id"] == ZONE_PARKING

    async def test_banos_se_degradan_porque_average_duration_min_no_llega(self, escenario):
        """GAP CONOCIDO, no un test que pasa por casualidad.

        `BathroomV1Model.duration_hours` exige `average_duration_min`
        (`bathroom_v1_model.py:156`). Ese campo existe en `ModelExecutionContext`
        pero `_build_execution_context` (stage4_model_execution.py:39) NO lo
        setea, y el helper que lo resolveria desde `service_configs`
        (`_resolve_service_duration`, prediction_module.py:145) esta definido
        pero nunca se llama.

        Consecuencia: en el path de prediccion, el modelo de banos NUNCA puede
        calcular y siempre degrada. Parking si funciona, porque
        `estimated_vehicles` si llega (viene de `event_day`).

        Este test fija el comportamiento ACTUAL a proposito: cuando se conecte
        `average_duration_min`, este test va a fallar y hay que invertirlo para
        exigir `model_result is not None`.
        """
        pred = await _pred(escenario["factory"], escenario["hoy"], 12)
        banos = _by_zone(pred)[ZONE_BANOS]
        assert banos.model_result is None, (
            "los banos YA calculan: significaria que average_duration_min "
            "llego al contexto. Invertir este assert para exigir "
            "model_result is not None."
        )
        assert banos.operational_state is not None, (
            "y la zona no puede desaparecer del resultado"
        )

    async def test_zona_generica_no_tiene_modelo_pero_sigue_saliendo(self, escenario):
        """Una zona sin modelo no desaparece: se resuelve con el contexto comun."""
        pred = await _pred(escenario["factory"], escenario["hoy"], 12)
        comida = _by_zone(pred)[ZONE_COMIDA]
        assert comida.model_result is None
        assert comida.operational_state is not None


class TestLaIntensidadMueveElModelo:
    async def test_la_fase_de_mayor_intensidad_proyecta_mas_ocupacion(self, escenario):
        """El objetivo del PASO 1, medido contra la BD.

        Apertura (intensity 0.1, 03:00) vs Clausura (intensity 1.0, 23:00) sobre
        el mismo parking. Antes de conectar los modelos esto daba exactamente
        igual, porque `intensity` no llegaba a ningun calculo.
        """
        factory, hoy = escenario["factory"], escenario["hoy"]
        baja = _by_zone(await _pred(factory, hoy, 3))[ZONE_PARKING]
        alta = _by_zone(await _pred(factory, hoy, 23))[ZONE_PARKING]

        ratio_bajo = baja.model_result["occupancy_ratio"]
        ratio_alto = alta.model_result["occupancy_ratio"]

        assert ratio_alto > ratio_bajo, (
            f"la intensidad de fase no movio el modelo: Apertura(0.1)={ratio_bajo}, "
            f"Clausura(1.0)={ratio_alto}. Si son iguales, intensity sigue sin llegar."
        )

    async def test_el_resto_de_las_zonas_no_cambia_con_la_fase(self, escenario):
        """Control: la zona generica no tiene modelo, asi que su densidad
        proyectada NO debe variar entre fases. Si variara, estariamos midiendo
        otra cosa."""
        factory, hoy = escenario["factory"], escenario["hoy"]
        baja = _by_zone(await _pred(factory, hoy, 3))[ZONE_COMIDA]
        alta = _by_zone(await _pred(factory, hoy, 23))[ZONE_COMIDA]
        assert baja.projected_density == alta.projected_density


class TestDegradacionGracefulEnBD:
    async def test_parking_sin_estimated_vehicles_no_rompe(self, engine, escenario):
        """El escenario de produccion que motivaba el try/except:
        `event_days.estimated_vehicles` es NULLABLE y ParkingV1 lo exige."""
        factory, hoy = escenario["factory"], escenario["hoy"]
        async with engine.begin() as conn:
            await conn.execute(
                sa.text("UPDATE event_days SET estimated_vehicles = NULL WHERE id = :d"),
                {"d": EVENT_DAY_ID},
            )
        try:
            pred = await _pred(factory, hoy, 12)
            assert pred is not None
            assert len(pred.zone_states) == 3, (
                "una zona sin insumo no puede reducir el numero de zonas"
            )
            states = _by_zone(pred)
            assert states[ZONE_PARKING].model_result is None
            # El resto sigue intacto: la degradacion es por zona. Se usa la zona
            # generica como referencia porque banos ya degrada siempre (ver
            # `test_banos_se_degradan_...`).
            assert states[ZONE_COMIDA].operational_state is not None
        finally:
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text("UPDATE event_days SET estimated_vehicles = 200 WHERE id = :d"),
                    {"d": EVENT_DAY_ID},
                )

    async def test_banos_sin_attendance_level_no_rompe(self, engine, escenario):
        """El otro insumo NULLABLE: `attendance_level.max_people`."""
        factory, hoy = escenario["factory"], escenario["hoy"]
        async with engine.begin() as conn:
            await conn.execute(
                sa.text("UPDATE event_days SET attendance_level_id = NULL WHERE id = :d"),
                {"d": EVENT_DAY_ID},
            )
        try:
            pred = await _pred(factory, hoy, 12)
            assert pred is not None
            assert len(pred.zone_states) == 3
            states = _by_zone(pred)
            assert states[ZONE_BANOS].model_result is None
            assert states[ZONE_PARKING].model_result is not None
        finally:
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text("UPDATE event_days SET attendance_level_id = :a WHERE id = :d"),
                    {"a": ATTENDANCE_ID, "d": EVENT_DAY_ID},
                )

    async def test_sin_ningun_insumo_sigue_habiendo_prediccion(self, engine, escenario):
        """Peor caso: los dos insumos NULL a la vez. La prediccion tiene que
        salir igual, con las tres zonas y sin resultados de modelo."""
        factory, hoy = escenario["factory"], escenario["hoy"]
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "UPDATE event_days SET estimated_vehicles = NULL, "
                    "attendance_level_id = NULL WHERE id = :d"
                ),
                {"d": EVENT_DAY_ID},
            )
        try:
            pred = await _pred(factory, hoy, 12)
            assert pred is not None
            assert len(pred.zone_states) == 3
            assert all(z.model_result is None for z in pred.zone_states)
        finally:
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        "UPDATE event_days SET estimated_vehicles = 200, "
                        "attendance_level_id = :a WHERE id = :d"
                    ),
                    {"a": ATTENDANCE_ID, "d": EVENT_DAY_ID},
                )