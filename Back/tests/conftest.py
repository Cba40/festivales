import os
from datetime import date, datetime, timedelta, timezone
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
        "rules": {"tipo": "minutos", "campo_inicio": None, "campo_fin": "activity_peak_start_min"},
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
        "rules": {"tipo": "minutos", "campo_inicio": "activity_peak_start_min", "campo_fin": "activity_peak_end_min"},
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
        "rules": {"tipo": "minutos", "campo_inicio": "activity_peak_end_min", "campo_fin": "exit_start_min"},
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
        "rules": {"tipo": "minutos", "campo_inicio": "exit_start_min", "campo_fin": "event_end_min"},
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
        "rules": {"tipo": "minutos", "campo_inicio": "event_end_min", "campo_fin": None},
    },
]


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
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
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
        entry_start_min=480,
        activity_peak_start_min=600,
        activity_peak_end_min=660,
        exit_start_min=1200,
        event_end_min=1380,
        estimated_attendance=50000,
        is_active=True,
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
        entry_start_min=1320,
        activity_peak_start_min=1380,
        activity_peak_end_min=1440,
        exit_start_min=1560,
        event_end_min=1620,
        estimated_attendance=30000,
        is_active=True,
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
        entry_start_min=480,
        activity_peak_start_min=600,
        activity_peak_end_min=660,
        exit_start_min=1200,
        event_end_min=1380,
        estimated_attendance=60000,
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
def sample_attendance_levels(db_session: Session, sample_event: Event) -> list:
    from app.models.attendance_level import AttendanceLevel
    levels = [
        AttendanceLevel(id="al-baja", event_id=sample_event.id, name="Baja", min_people=0, max_people=5000, global_multiplier=0.8),
        AttendanceLevel(id="al-media", event_id=sample_event.id, name="Media", min_people=5001, max_people=15000, global_multiplier=1.0),
        AttendanceLevel(id="al-alta", event_id=sample_event.id, name="Alta", min_people=15001, max_people=30000, global_multiplier=1.3),
        AttendanceLevel(id="al-muy-alta", event_id=sample_event.id, name="Muy Alta", min_people=30001, max_people=60000, global_multiplier=1.6),
        AttendanceLevel(id="al-masiva", event_id=sample_event.id, name="Masiva", min_people=60001, max_people=None, global_multiplier=2.0),
    ]
    for al in levels:
        db_session.add(al)
    db_session.flush()
    return levels


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
