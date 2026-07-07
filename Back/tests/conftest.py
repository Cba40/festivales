import os
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.session import Base, get_db
from app.main import app
from app.models.event import Event
from app.models.event_day import EventDay
from app.models.event_day_zone_factor import EventDayZoneFactor
from app.models.event_state import EventState
from app.models.incident import Incident
from app.models.incident_impact import IncidentImpact
from app.models.state_override import StateOverride
from app.models.zone import Zone
from app.models.zone_type import ZoneType

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", settings.DATABASE_URL)

EVENT_STATE_IDS = {
    "pre_apertura": "a1111111-1111-1111-1111-111111111111",
    "temprano": "a2222222-2222-2222-2222-222222222222",
    "pico": "a3333333-3333-3333-3333-333333333333",
    "cierre": "a4444444-4444-4444-4444-444444444444",
    "post_evento": "a5555555-5555-5555-5555-555555555555",
}

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

EVENT_STATE_SEEDS = [
    {
        "id": EVENT_STATE_IDS["pre_apertura"],
        "event_id": None,
        "name": "Pre-apertura",
        "slug": "pre_apertura",
        "sort_order": 0,
        "color": "#94a3b8",
        "description": "Apertura de puertas.",
        "is_initial": True,
        "is_final": False,
        "rules": {"tipo": "horario", "campo_inicio": None, "campo_fin": "entry_peak_start_time"},
    },
    {
        "id": EVENT_STATE_IDS["temprano"],
        "event_id": None,
        "name": "Temprano",
        "slug": "temprano",
        "sort_order": 1,
        "color": "#3b82f6",
        "description": "Pico de ingreso.",
        "is_initial": False,
        "is_final": False,
        "rules": {"tipo": "horario", "campo_inicio": "entry_peak_start_time", "campo_fin": "event_start_time"},
    },
    {
        "id": EVENT_STATE_IDS["pico"],
        "event_id": None,
        "name": "Pico",
        "slug": "pico",
        "sort_order": 2,
        "color": "#ef4444",
        "description": "Show principal en curso.",
        "is_initial": False,
        "is_final": False,
        "rules": {"tipo": "horario", "campo_inicio": "event_start_time", "campo_fin": "exit_peak_start_time"},
    },
    {
        "id": EVENT_STATE_IDS["cierre"],
        "event_id": None,
        "name": "Cierre",
        "slug": "cierre",
        "sort_order": 3,
        "color": "#f59e0b",
        "description": "Pico de salida.",
        "is_initial": False,
        "is_final": False,
        "rules": {"tipo": "horario", "campo_inicio": "exit_peak_start_time", "campo_fin": "event_end_time"},
    },
    {
        "id": EVENT_STATE_IDS["post_evento"],
        "event_id": None,
        "name": "Post-evento",
        "slug": "post_evento",
        "sort_order": 4,
        "color": "#6366f1",
        "description": "Jornada finalizada.",
        "is_initial": False,
        "is_final": True,
        "rules": {"tipo": "horario", "campo_inicio": "event_end_time", "campo_fin": None},
    },
]


def _create_check_function(engine):
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION check_event_day_time_order(
                p_t1 TIME, p_t2 TIME, p_t3 TIME, p_t4 TIME,
                p_t5 TIME, p_t6 TIME, p_t7 TIME
            ) RETURNS BOOLEAN
            LANGUAGE plpgsql IMMUTABLE RETURNS NULL ON NULL INPUT
            AS $$
            DECLARE
                v_t1 INTEGER; v_t2 INTEGER; v_t3 INTEGER; v_t4 INTEGER;
                v_t5 INTEGER; v_t6 INTEGER; v_t7 INTEGER;
            BEGIN
                v_t1 := EXTRACT(EPOCH FROM p_t1)::INTEGER;
                v_t2 := EXTRACT(EPOCH FROM p_t2)::INTEGER;
                v_t3 := EXTRACT(EPOCH FROM p_t3)::INTEGER;
                v_t4 := EXTRACT(EPOCH FROM p_t4)::INTEGER;
                v_t5 := EXTRACT(EPOCH FROM p_t5)::INTEGER;
                v_t6 := EXTRACT(EPOCH FROM p_t6)::INTEGER;
                v_t7 := EXTRACT(EPOCH FROM p_t7)::INTEGER;

                IF v_t2 < v_t1 THEN v_t2 := v_t2 + 86400; END IF;
                IF v_t3 < v_t2 THEN v_t3 := v_t3 + 86400; END IF;
                IF v_t4 < v_t3 THEN v_t4 := v_t4 + 86400; END IF;
                IF v_t5 < v_t4 THEN v_t5 := v_t5 + 86400; END IF;
                IF v_t6 < v_t5 THEN v_t6 := v_t6 + 86400; END IF;
                IF v_t7 < v_t6 THEN v_t7 := v_t7 + 86400; END IF;

                IF v_t1 >= v_t2 THEN RETURN FALSE; END IF;
                IF v_t2 >= v_t3 THEN RETURN FALSE; END IF;
                IF v_t3 >= v_t4 THEN RETURN FALSE; END IF;
                IF v_t4 >= v_t5 THEN RETURN FALSE; END IF;
                IF v_t5 >= v_t6 THEN RETURN FALSE; END IF;
                IF v_t6 >= v_t7 THEN RETURN FALSE; END IF;

                RETURN TRUE;
            END;
            $$;
        """))
        conn.commit()


def _drop_check_function(engine):
    with engine.connect() as conn:
        conn.execute(text("DROP FUNCTION IF EXISTS check_event_day_time_order"))
        conn.commit()


def _seed_event_states(session: Session):
    for data in EVENT_STATE_SEEDS:
        exists = session.get(EventState, data["id"])
        if not exists:
            session.add(EventState(**data))


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


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    _create_check_function(engine)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    _drop_check_function(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    session.begin_nested()

    _seed_event_states(session)
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
        entry_start_time=time(8, 0),
        entry_peak_start_time=time(10, 0),
        entry_peak_end_time=time(11, 0),
        event_start_time=time(13, 0),
        exit_peak_start_time=time(20, 0),
        exit_peak_end_time=time(21, 0),
        event_end_time=time(23, 0),
        is_active=True,
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
