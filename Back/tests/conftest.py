import asyncio
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pytest
from fastapi.testclient import TestClient

# Windows: psycopg async requires SelectorEventLoop, not ProactorEventLoop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from jose import jwt
from sqlalchemy import DefaultClause, String, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.event import Event
from app.models.event_day import EventDay
from app.models.event_day_phase import EventDayPhase
from app.models.zone import Zone
from app.models.zone_type import ZoneType
from src.infrastructure.middleware.rate_limit import reset_backend_sync

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", settings.DATABASE_URL)

# ── Guard de seguridad ───────────────────────────────────────────────
#
# El fixture `test_engine` de abajo BORRA el schema `public` de TEST_DATABASE_URL
# al empezar y al terminar la sesion. Si esa URL apunta por error a la base de
# desarrollo, la suite destruye el esquema y la cadena de Alembic.
#
# Ya paso: `TEST_DATABASE_URL` no estaba definida, con caia al fallback
# `settings.DATABASE_URL` (que es la de DESARROLLO) y los tests corrían `drop_all`
# contra ella. Por eso se exige un nombre de base que termine en `_test`, en vez
# de confiar en que la variable este bien puesta.
#
# Para correr los tests hay que tener `TEST_DATABASE_URL` en `Back/.env`
# apuntando a una base `_test`. Se puede sobreescribir por proceso con la misma
# variable de entorno.
# ────────────────────────────────────────────────────────────────────
_DB_NAME = TEST_DATABASE_URL.rsplit("/", 1)[-1].split("?")[0]
if not _DB_NAME.endswith("_test"):
    raise RuntimeError(
        "SECURITY BLOCK: la suite de tests borra el schema `public` de la base a "
        "la que apunta TEST_DATABASE_URL, asi que el nombre debe terminar en "
        f"`_test`. Se resolvio {_DB_NAME!r}. Configura TEST_DATABASE_URL en "
        f"{Path(__file__).resolve().parents[1] / '.env'} apuntando a una base de "
        "test (por ejemplo `.../territorial_mvp_test`)."
    )

ZONE_TYPE_IDS = {
    "puesto_comida": "b1111111-1111-1111-1111-111111111111",
    "bano": "b2222222-2222-2222-2222-222222222222",
    "emergencia": "b3333333-3333-3333-3333-333333333333",
    "hidratacion": "b4444444-4444-4444-4444-444444444444",
    "ingreso": "b5555555-5555-5555-5555-555555555555",
    "escenario": "b6666666-6666-6666-6666-666666666666",
}

ZONE_TYPE_DEFAULT_FACTORS = {
    "puesto_comida": {
        "pre_apertura": {"saturation": 0.0, "attendance": 0.0, "resource": 0.3},
        "temprano": {"saturation": 0.4, "attendance": 0.5, "resource": 0.6},
        "pico": {"saturation": 1.2, "attendance": 1.5, "resource": 1.0},
        "cierre": {"saturation": 0.8, "attendance": 0.6, "resource": 0.5},
        "post_evento": {"saturation": 0.2, "attendance": 0.1, "resource": 0.2},
    },
    "bano": {
        "pre_apertura": {"saturation": 0.0, "attendance": 0.0, "resource": 0.5},
        "temprano": {"saturation": 0.3, "attendance": 0.4, "resource": 0.7},
        "pico": {"saturation": 1.5, "attendance": 1.3, "resource": 1.2},
        "cierre": {"saturation": 1.0, "attendance": 0.8, "resource": 0.8},
        "post_evento": {"saturation": 0.5, "attendance": 0.3, "resource": 0.4},
    },
    "emergencia": {
        "pre_apertura": {"saturation": 0.0, "attendance": 0.0, "resource": 1.0},
        "temprano": {"saturation": 0.2, "attendance": 0.3, "resource": 1.0},
        "pico": {"saturation": 0.8, "attendance": 0.7, "resource": 1.5},
        "cierre": {"saturation": 0.4, "attendance": 0.3, "resource": 1.2},
        "post_evento": {"saturation": 0.1, "attendance": 0.1, "resource": 0.8},
    },
    "hidratacion": {
        "pre_apertura": {"saturation": 0.0, "attendance": 0.0, "resource": 0.4},
        "temprano": {"saturation": 0.5, "attendance": 0.6, "resource": 0.6},
        "pico": {"saturation": 1.3, "attendance": 1.4, "resource": 1.1},
        "cierre": {"saturation": 0.7, "attendance": 0.5, "resource": 0.5},
        "post_evento": {"saturation": 0.3, "attendance": 0.2, "resource": 0.3},
    },
    "ingreso": {
        "pre_apertura": {"saturation": 1.5, "attendance": 1.8, "resource": 1.5},
        "temprano": {"saturation": 1.2, "attendance": 1.5, "resource": 1.2},
        "pico": {"saturation": 0.3, "attendance": 0.4, "resource": 0.6},
        "cierre": {"saturation": 0.1, "attendance": 0.2, "resource": 0.4},
        "post_evento": {"saturation": 0.0, "attendance": 0.0, "resource": 0.2},
    },
    "escenario": {
        "pre_apertura": {"saturation": 0.0, "attendance": 0.0, "resource": 0.5},
        "temprano": {"saturation": 0.6, "attendance": 0.8, "resource": 0.7},
        "pico": {"saturation": 1.8, "attendance": 2.0, "resource": 1.5},
        "cierre": {"saturation": 0.5, "attendance": 0.4, "resource": 1.0},
        "post_evento": {"saturation": 0.1, "attendance": 0.1, "resource": 0.3},
    },
}


def _seed_zone_types(session: Session):
    for slug, factors in ZONE_TYPE_DEFAULT_FACTORS.items():
        obj_id = ZONE_TYPE_IDS[slug]
        exists = session.get(ZoneType, obj_id)
        if not exists:
            names = {
                "puesto_comida": "Puesto de comida",
                "bano": "Baño",
                "emergencia": "Emergencia",
                "hidratacion": "Puesto de hidratación",
                "ingreso": "Ingreso / Control",
                "escenario": "Escenario",
            }
            icons = {
                "puesto_comida": "utensils-crossed",
                "bano": "toilet",
                "emergencia": "tent",
                "hidratacion": "droplets",
                "ingreso": "scan-eye",
                "escenario": "stage",
            }
            session.add(ZoneType(
                id=obj_id,
                name=names[slug],
                slug=slug,
                icon=icons[slug],
                description=names[slug],
                default_factors=factors,
            ))


_TEST_GEOMETRY_GEOM_COLUMNS = [
    (table.c[column_name], column.type)
    for table in Base.metadata.tables.values()
    for column_name, column in table.columns.items()
    if "geometry" in column.type.__class__.__name__.lower()
]
_TEST_GEOMETRY_INDEXES = [
    index
    for table in Base.metadata.tables.values()
    for index in table.indexes
    if "geometry" in [c.name for c in index.columns]
]
_TEST_INTENSITY_COLUMN = EventDayPhase.__table__.c.intensity
_TEST_INTENSITY_DEFAULT = _TEST_INTENSITY_COLUMN.server_default


def _degrade_geometry_for_tests() -> None:
    """Ajusta el DDL para que `create_all` funcione sin PostGIS.

    Dos bugs de los modelos, ya parcheados aparte en `test_crud_p3.py` y
    `test_recommendation_flow.py`. Se corrigen aqui para el DDL de la sesion.

    1. El entorno local no tiene PostGIS (no esta en `pg_available_extensions` ni
       hay binarios en disco), asi que `create_all` falla con
       `UndefinedObject: no existe el tipo «geometry»`, y un `SELECT` que proyecte
       la columna muere en `ST_AsEWKB`. Antes esto no se notaba porque la base
       arrastraba una `zones.geometry` ya degradada a VARCHAR de una epoca
       anterior. Los tests de este modulo solo leen `zone.id` y `zone.capacity`.

       Hay que tocar el tipo y no solo el DDL, porque el problema esta en la
       expresion del SELECT, no en la definicion de la tabla.

    2. `EventDayPhase.intensity` declara `server_default=func.text('1.0')` sobre
       una columna `Float`, y Postgres rechaza un default de tipo `text` sobre
       `double precision` (DatatypeMismatch).
    """
    for column, _ in _TEST_GEOMETRY_GEOM_COLUMNS:
        column.type = String()
    for index in _TEST_GEOMETRY_INDEXES:
        index.table.indexes.discard(index)
    _TEST_INTENSITY_COLUMN.server_default = DefaultClause(text("1.0"))


def _restore_geometry_after_tests() -> None:
    for column, original_type in _TEST_GEOMETRY_GEOM_COLUMNS:
        column.type = original_type
    for index in _TEST_GEOMETRY_INDEXES:
        index.table.indexes.add(index)
    _TEST_INTENSITY_COLUMN.server_default = _TEST_INTENSITY_DEFAULT


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    # Antes era `Base.metadata.drop_all(bind=engine)`, que fallaba con
    # `DependentObjectsStillExist`: 7 tablas de la base (zone_subtypes,
    # zone_recommendations, predictions, operational_observations,
    # configuration_recommendations, knowledge_model_versions,
    # recommendation_audit_log) NO estan en `app.db.session.Base.metadata`, asi
    # que `drop_all` no las borraba y sus FKs bloqueaban el DROP de `event_days`.
    # Eso abortaba el drop entero y el `create_all` siguiente nunca corria,
    # tumbando 64 tests de 5 archivos en el setup.
    #
    # `DROP SCHEMA ... CASCADE` borra lo que haya, este o no en el metadata, y en
    # el orden correcto. Es idempotente y no depende de las tablas que SQLAlchemy
    # conozca. El guard de arriba garantiza que esta base termina en `_test`.
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    # La degradacion se mantiene durante TODA la sesion, no solo durante el
    # `create_all`: el mismo `ST_GeomFromEWKT` aparece en el `INSERT` de un `Zone`
    # a traves del bind param de la columna, asi que restaurar el tipo aqui
    # hacia fallar igual en el setup de los tests que si insertan zonas.
    _degrade_geometry_for_tests()
    try:
        Base.metadata.create_all(bind=engine)
        yield engine
    finally:
        _restore_geometry_after_tests()
        with engine.begin() as conn:
            conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    session.begin_nested()

    _seed_zone_types(session)
    session.flush()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def sample_event(db_session: Session) -> Event:
    event = Event(id="test-event-1", name="Test Event", description="Test")
    db_session.add(event)
    db_session.flush()
    return event


@pytest.fixture
def sample_event_day(db_session: Session, sample_event: Event) -> EventDay:
    day = EventDay(
        id="test-day-1",
        event_id=sample_event.id,
        date=date(2026, 7, 10),
        day_of_week="viernes",
        is_active=True,
        operational_start_min=480,
        operational_end_min=1320,
    )
    db_session.add(day)
    db_session.flush()
    return day


@pytest.fixture
def sample_event_day_cross_midnight(db_session: Session, sample_event: Event) -> EventDay:
    day = EventDay(
        id="test-day-cross",
        event_id=sample_event.id,
        date=date(2026, 7, 10),
        day_of_week="viernes",
        is_active=True,
        operational_start_min=480,
        operational_end_min=1320,
    )
    db_session.add(day)
    db_session.flush()
    return day


@pytest.fixture
def sample_event_day_next(db_session: Session, sample_event: Event) -> EventDay:
    day = EventDay(
        id="test-day-next",
        event_id=sample_event.id,
        date=date(2026, 7, 11),
        day_of_week="sabado",
        is_active=True,
        operational_start_min=480,
        operational_end_min=1320,
    )
    db_session.add(day)
    db_session.flush()
    return day


@pytest.fixture
def sample_zones(db_session: Session, sample_event: Event) -> list[Zone]:
    zones = [
        Zone(
            id="zone-comida-1",
            event_id=sample_event.id,
            name="Comida Norte",
            type="puesto_comida",
            saturation="bajo",
            status="activa",
            capacity=100,
            available_capacity=80,
        ),
        Zone(
            id="zone-bano-1",
            event_id=sample_event.id,
            name="Baño Sur",
            type="bano",
            saturation="bajo",
            status="activa",
            capacity=50,
            available_capacity=30,
        ),
        Zone(
            id="zone-emergencia-1",
            event_id=sample_event.id,
            name="Emergencia Central",
            type="emergencia",
            saturation="bajo",
            status="activa",
            capacity=20,
            available_capacity=18,
        ),
    ]
    for z in zones:
        db_session.add(z)
    db_session.flush()
    return zones


@pytest.fixture
def sample_attendance_levels(db_session: Session, sample_event: Event, sample_event_day: EventDay) -> list:
    from app.models.attendance_level import AttendanceLevel
    levels = [
        AttendanceLevel(id="al-baja", event_id=sample_event.id, name="Baja", min_people=0, max_people=5000),
        AttendanceLevel(id="al-media", event_id=sample_event.id, name="Media", min_people=5001, max_people=15000),
        AttendanceLevel(id="al-alta", event_id=sample_event.id, name="Alta", min_people=15001, max_people=30000),
        AttendanceLevel(id="al-muy-alta", event_id=sample_event.id, name="Muy Alta", min_people=30001, max_people=60000),
        AttendanceLevel(id="al-masiva", event_id=sample_event.id, name="Masiva", min_people=60001, max_people=None),
    ]
    for al in levels:
        db_session.add(al)
    db_session.flush()
    return levels


@pytest.fixture(autouse=True)
def _reset_rate_limit_state():
    """Deja el rate limiter en cero antes de cada test.

    El backend en memoria es un singleton de proceso y el IP de `TestClient` es
    siempre la misma, asi que sin este reset los tests se consumirian entre si
    el limite (60/min en GET, 10/min en /activity, 5/min en /login) y una suite
    con mas de 60 llamadas a rutas publicas empezaria a fallar con 429 de forma
    dependiente del orden de ejecucion.

    Los tests propios de rate limit (tests/infrastructure/middleware/
    test_rate_limit.py) miden el limite a proposito y no dependen de este reset.

    El reset es **sincrono a proposito**. Con `asyncio.run(reset_backend())` este
    fixture abria y cerraba un event loop en cada uno de los ~1600 tests de la
    suite, y eso se cruzaba con los fixtures asincronos de scope modulo/sesion del
    resto (`Future attached to a different loop`,
    `asyncpg: another operation is in progress`). Se manifesto como 8 fallos en
    tests/models y tests/unit/test_crud_p3.py mas 5 errors en
    tests/crud/test_operational_observation.py, y solo al superar el numero de
    tests que hace falta para que los loops se solapen.
    """
    yield
    reset_backend_sync()


@pytest.fixture
def auth_headers() -> dict:
    expire = datetime.now(timezone.utc) + timedelta(hours=8)
    token = jwt.encode(
        {"sub": "admin", "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client(db_session: Session) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
