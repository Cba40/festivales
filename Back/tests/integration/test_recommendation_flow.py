"""Tests de integración del flujo completo de recomendaciones y audit log.

Ejecutan contra una instancia PostgreSQL real (sin mocks del workflow_service
ni de las rutas):
- Flujo directo vía ``RecommendationWorkflowServiceImpl.create_recommendation``.
- Endpoints HTTP reales (``POST /api/analytics/recommendations``,
  ``POST /api/analytics/recommendations/{id}/resolve``,
  ``GET /api/analytics/recommendations/{id}``, ``GET /api/analytics/audit-log``).
- Endpoint combinado ``POST /api/analytics/evaluate`` con dataset real del
  motor de predicción (Stage 1-5) sembrado en la BD.

Verifican que ``id``, ``km_version_analyzed``, ``recommendation_id`` y
``km_version`` se persisten como UUID nativos (nunca como ``str``).

Usan una BD PostgreSQL dedicada ``territorial_mvp_test`` (creada si no existe)
para no tocar la BD de desarrollo. No requieren PostGIS funcional: las tablas
que en producción tienen columnas ``geometry`` (``events``, ``zones``,
``points``) se crean en el test sin esa columna.
"""
from __future__ import annotations

import importlib
import sys
import threading
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.session import AsyncSessionLocal
from app.main import app
from src.infrastructure.persistence.models.configuration_recommendation import (
    ConfigurationRecommendation as ConfigModel,
)
from src.infrastructure.persistence.models.recommendation_audit_entry import (
    RecommendationAuditEntry as AuditModel,
)

TEST_DATABASE_NAME = "territorial_mvp_test"
TEST_ADMIN_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
TEST_DATABASE_URL = (
    f"postgresql+psycopg://postgres:postgres@localhost:5432/{TEST_DATABASE_NAME}"
)

ZONE_TYPE_ID = "b1111111-1111-1111-1111-111111111111"
PROFILE_ID = "c1111111-1111-1111-1111-111111111111"
PHASE_ID = "d1111111-1111-1111-1111-111111111111"
EVENT_ID = "intg-event-0001"
EVENT_DAY_ID = "11111111-1111-1111-1111-111111111111"
ZONE_ID = "22222222-2222-2222-2222-222222222222"
ATTENDANCE_ID = "33333333-3333-3333-3333-333333333333"

TABLES_TO_RESET = [
    "recommendation_audit_log",
    "configuration_recommendations",
    "predictions",
    "operational_observations",
    "operational_events",
    "zone_recommendations",
    "event_day_phases",
    "event_days",
    "zone_behaviors",
    "service_configs",
    "operational_phases",
    "operational_profiles",
    "attendance_levels",
    "knowledge_model_versions",
    "zones",
    "events",
    "zone_types",
    "recommendation_config",
    "stage4_config",
]

EVENTS_DDL = """
CREATE TABLE events (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    location VARCHAR(255),
    geometry VARCHAR(255),
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    reference_point_latitude FLOAT,
    reference_point_longitude FLOAT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

ZONES_DDL = """
CREATE TABLE zones (
    id VARCHAR(36) PRIMARY KEY,
    event_id VARCHAR(36) NOT NULL REFERENCES events(id),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    saturation VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    capacity INT NOT NULL,
    available_capacity INT NOT NULL,
    latitude FLOAT,
    longitude FLOAT,
    geometry VARCHAR(255),
    disponibilidad INT,
    espera_min INT,
    calle VARCHAR(255),
    subtipo VARCHAR(100),
    tipo_culinario VARCHAR(100),
    x FLOAT,
    y FLOAT,
    direccion VARCHAR(255),
    horario VARCHAR(100),
    telefono VARCHAR(50),
    web VARCHAR(255),
    servicios VARCHAR(500),
    transporte VARCHAR(50),
    capacidad_estimada INT,
    es_embudo BOOLEAN,
    geometry_type VARCHAR(10),
    coordinates JSON,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

POINTS_DDL = """
CREATE TABLE points (
    id VARCHAR(36) PRIMARY KEY,
    event_id VARCHAR(36) NOT NULL REFERENCES events(id),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100) NOT NULL,
    description TEXT,
    geometry VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""

_SESSION_FACTORY_TARGETS = [
    ("app.db.session", "AsyncSessionLocal"),
    ("app.api.routes.analytics", "async_session_maker"),
    (
        "src.infrastructure.persistence.repositories.configuration_recommendation_repository",
        "AsyncSessionLocal",
    ),
    (
        "src.infrastructure.persistence.repositories.recommendation_audit_entry_repository",
        "AsyncSessionLocal",
    ),
]

_SCHEMA_LOCK = threading.Lock()
_SCHEMA_READY = False


def _ensure_test_database() -> None:
    engine = create_engine(TEST_ADMIN_URL, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": TEST_DATABASE_NAME},
            ).scalar()
            if not exists:
                conn.execute(text(f"CREATE DATABASE {TEST_DATABASE_NAME}"))
    finally:
        engine.dispose()


def _ensure_test_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return
    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return
        _ensure_test_database()
        engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        try:
            with engine.begin() as conn:
                conn.execute(text("CREATE SEQUENCE IF NOT EXISTS km_version_number_seq"))
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE IF EXISTS points"))
                conn.execute(text("DROP TABLE IF EXISTS zones CASCADE"))
                conn.execute(text("DROP TABLE IF EXISTS events CASCADE"))
                conn.execute(text(EVENTS_DDL))
                conn.execute(text(ZONES_DDL))
                conn.execute(text(POINTS_DDL))
            # create_all hace checkfirst: omite events/zones/points (pre-creadas).
            from app.db.session import Base as AppBase

            # Bug pre-existente de los modelos: `func.text('1.0')` genera un
            # default de tipo text sobre columna float, que Postgres rechaza.
            # Se corrige solo para el DDL de test (no modifica el código app).
            from sqlalchemy import DefaultClause

            from app.models.event_day_phase import EventDayPhase as AppEventDayPhase

            from src.infrastructure.persistence.models.event_day_phase import (
                EventDayPhaseModel as InfraEventDayPhaseModel,
            )

            for model in (AppEventDayPhase, InfraEventDayPhaseModel):
                model.__table__.c.intensity.server_default = DefaultClause(text("1.0"))

            # Las tablas events/zones/points se pre-crean sin la columna postgis
            # (el servidor no tiene la librería postgis-3 operativa). Si la
            # columna geometry sigue mapeada como Geometry(), la ORM emite
            # ST_GeomFromEWKT(...) incluso con NULL; por eso se degrada el tipo
            # a VARCHAR en memoria (solo afecta a la sesión de test).
            from sqlalchemy import String

            from app.models.event import Event
            from app.models.point import Point
            from app.models.zone import Zone

            for model in (Event, Zone, Point):
                model.__table__.c.geometry.type = String()

            AppBase.metadata.create_all(bind=engine)
            from src.infrastructure.db.base import Base as InfraBase

            InfraBase.metadata.create_all(bind=engine)
        finally:
            engine.dispose()
        _SCHEMA_READY = True


@pytest.fixture
def real_db(monkeypatch):
    """Apunta las fábricas de sesión alásticas a la BD de test dedicada."""
    _ensure_test_schema()
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    for module_name, attr in _SESSION_FACTORY_TARGETS:
        monkeypatch.setattr(importlib.import_module(module_name), attr, factory)
    monkeypatch.setattr(sys.modules[__name__], "AsyncSessionLocal", factory)
    return factory


@pytest.fixture
async def clean_db(real_db):
    async with AsyncSessionLocal() as session:
        for table in TABLES_TO_RESET:
            await session.execute(text(f"DELETE FROM {table}"))
        await session.commit()
    yield


async def _seed_pipeline_dataset() -> None:
    """Siembra el dataset mínimo para predecir densidad y generar una anomalía.

    predicted = capacity(100) * density_factor(0.5) = 50; observed = 95
    ⇒ desviación |50-95|/100 = 0.45 > umbral 0.2 ⇒ anomalía de densidad.
    """
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
    from src.application.context_engine.stage1_context_resolution import LOCAL_TZ
    from src.infrastructure.persistence.models.operational_observation import (
        OperationalObservationModel,
    )

    local_today = datetime.now(LOCAL_TZ).date()

    async with AsyncSessionLocal() as session:
        session.add_all(
            [
                RecommendationConfigModel(id=1),
                Stage4ConfigModel(id=1),
                OperationalProfile(
                    id=UUID(PROFILE_ID),
                    name="PerfilIntegracion",
                    description="Perfil de prueba de integración",
                ),
                OperationalPhase(
                    id=UUID(PHASE_ID),
                    operational_profile_id=UUID(PROFILE_ID),
                    name="Pico",
                    sort_order=1,
                ),
                Event(id=EVENT_ID, name="Evento Integracion", description="test"),
                ZoneType(
                    id=ZONE_TYPE_ID,
                    name="Puesto de comida",
                    slug="puesto_comida",
                    icon="utensils-crossed",
                    description="Puesto de comida",
                    default_factors={},
                ),
                AttendanceLevel(
                    id=ATTENDANCE_ID,
                    event_id=EVENT_ID,
                    name="Alta",
                    min_people=0,
                    max_people=10000,
                ),
                EventDay(
                    id=EVENT_DAY_ID,
                    event_id=EVENT_ID,
                    date=local_today,
                    day_of_week="viernes",
                    is_active=True,
                    attendance_level_id=ATTENDANCE_ID,
                    operational_profile_id=UUID(PROFILE_ID),
                    operational_start_min=0,
                    operational_end_min=1440,
                ),
                EventDayPhase(
                    event_day_id=EVENT_DAY_ID,
                    operational_phase_id=UUID(PHASE_ID),
                    start_min=0,
                    end_min=1439,
                    intensity=1.0,
                ),
                Zone(
                    id=ZONE_ID,
                    event_id=EVENT_ID,
                    name="Comida Norte",
                    type="puesto_comida",
                    saturation="bajo",
                    status="activa",
                    capacity=100,
                    available_capacity=80,
                ),
                ZoneBehavior(
                    zone_type_id=ZONE_TYPE_ID,
                    operational_phase_id=UUID(PHASE_ID),
                    density_factor=0.5,
                    flow_restriction="OPEN",
                ),
                OperationalObservationModel(
                    event_day_id=EVENT_DAY_ID,
                    zone_id=ZONE_ID,
                    timestamp=datetime.now(timezone.utc) - timedelta(minutes=2),
                    observed_density=95,
                    source="integration-test",
                ),
            ]
        )
        await session.commit()


@pytest.fixture
def domain_recommendation():
    from app.api.routes.analytics import _build_recommendation
    from app.schemas.analytics import EvaluationRequest
    from src.application.learning.anomaly_detector import Anomaly

    anomaly = Anomaly(
        metric_name="density_deviation",
        severity="high",
        description="Desviación alta de densidad",
        suggested_action="Revisar distribución de recursos",
        value=0.45,
        is_provisional=True,
    )
    request = EvaluationRequest(event_day_id=EVENT_DAY_ID, phase_id=PHASE_ID)
    return _build_recommendation(anomaly, request)


def _workflow_service():
    from src.infrastructure.notifications.stub_notification_service import (
        StubNotificationService,
    )
    from src.infrastructure.persistence.repositories.configuration_recommendation_repository import (
        SQLConfigurationRecommendationRepository,
    )
    from src.infrastructure.persistence.repositories.recommendation_audit_entry_repository import (
        SQLRecommendationAuditEntryRepository,
    )
    from src.application.learning.workflow_service import (
        RecommendationWorkflowServiceImpl,
    )

    return RecommendationWorkflowServiceImpl(
        repo=SQLConfigurationRecommendationRepository(),
        audit_repo=SQLRecommendationAuditEntryRepository(),
        notification_service=StubNotificationService(),
    )


@pytest.mark.asyncio
async def test_workflow_persists_recommendation_and_audit_with_native_uuids(
    clean_db, domain_recommendation
):
    created = await _workflow_service().create_recommendation(domain_recommendation)
    assert isinstance(created.id, UUID)

    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                select(ConfigModel).where(ConfigModel.id == created.id)
            )
        ).scalar_one()
        assert isinstance(row.id, UUID)
        assert row.id == created.id
        assert row.status == "pending_review"
        assert row.km_version_analyzed is None or isinstance(
            row.km_version_analyzed, UUID
        )

        audits = (
            await session.execute(
                select(AuditModel).where(AuditModel.recommendation_id == created.id)
            )
        ).scalars().all()
        assert len(audits) == 1
        assert audits[0].action == "generated"
        assert isinstance(audits[0].id, UUID)
        assert isinstance(audits[0].recommendation_id, UUID)
        assert audits[0].recommendation_id == created.id
        assert audits[0].km_version is None or isinstance(audits[0].km_version, UUID)


@pytest.mark.asyncio
async def test_create_recommendation_endpoint_persists_and_reads_back(
    clean_db, auth_headers
):
    payload = {
        "target_entity_type": "event_day",
        "target_entity_id": EVENT_DAY_ID,
        "proposed_change": "Revisar distribución de recursos",
        "recommendation_type": "parameter_adjustment",
        "supporting_metrics": {"metric": "density_deviation", "value": 0.45},
        "historic_trace": {
            "prediction_ids": [],
            "observation_ids": [],
            "operational_event_ids": [],
        },
        "recommendation_confidence": 0.9,
        "event_ids": None,
        "km_version_analyzed": None,
        "algorithm_version": "etapa2-v1",
    }
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/analytics/recommendations", json=payload, headers=auth_headers
        )
    assert resp.status_code == 201, resp.text
    rec_id = UUID(resp.json()["id"])
    assert resp.json()["status"] == "pending_review"

    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(
                select(ConfigModel).where(ConfigModel.id == rec_id)
            )
).scalar_one()
        assert isinstance(row.id, UUID)
        assert row.status == "pending_review"
        assert row.recommendation_type == "parameter_adjustment"
        assert row.supporting_metrics is not None
        assert row.supporting_metrics["metric"] == "density_deviation"
        assert row.supporting_metrics["value"] == 0.45

        audits = (
            await session.execute(
                select(AuditModel).where(AuditModel.recommendation_id == rec_id)
            )
        ).scalars().all()
        assert len(audits) == 1
        assert audits[0].action == "generated"
        assert isinstance(audits[0].id, UUID)
        assert isinstance(audits[0].recommendation_id, UUID)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/api/analytics/recommendations/{rec_id}", headers=auth_headers
        )
    assert resp.status_code == 200, resp.text
    assert UUID(resp.json()["id"]) == rec_id
    assert resp.json()["status"] == "pending_review"


@pytest.mark.asyncio
async def test_resolve_recommendation_updates_and_audits(
    clean_db, auth_headers, domain_recommendation
):
    created = await _workflow_service().create_recommendation(domain_recommendation)
    rec_id = created.id

    payload = {
        "approved": True,
        "operator_id": "operator-integration",
        "justification": "ok",
    }
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            f"/api/analytics/recommendations/{rec_id}/resolve",
            json=payload,
            headers=auth_headers,
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "approved"
    assert resp.json()["resolved_by"] == "operator-integration"

    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(select(ConfigModel).where(ConfigModel.id == rec_id))
        ).scalar_one()
        assert row.status == "approved"
        assert row.resolved_by == "operator-integration"

        audits = (
            await session.execute(
                select(AuditModel).where(AuditModel.recommendation_id == rec_id)
            )
        ).scalars().all()
        assert {a.action for a in audits} == {"generated", "resolved"}
        assert all(
            isinstance(a.id, UUID) and isinstance(a.recommendation_id, UUID)
            for a in audits
        )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/api/analytics/audit-log?recommendation_id={rec_id}",
            headers=auth_headers,
        )
    assert resp.status_code == 200, resp.text
    entries = resp.json()
    assert {e["action"] for e in entries} == {"generated", "resolved"}
    assert all(e["recommendation_id"] == str(rec_id) for e in entries)
    assert all(UUID(e["id"]) for e in entries)


@pytest.mark.asyncio
async def test_evaluate_endpoint_creates_real_recommendation_and_audit(
    clean_db, auth_headers
):
    await _seed_pipeline_dataset()

    payload = {"event_day_id": EVENT_DAY_ID, "phase_id": PHASE_ID}
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/analytics/evaluate", json=payload, headers=auth_headers
        )
    assert resp.status_code == 200, resp.text

    body = resp.json()
    assert body["anomalies_detected"] == 1
    assert len(body["recommendations_created"]) == 1
    rec_id = UUID(body["recommendations_created"][0]["id"])
    assert body["recommendations_created"][0]["status"] == "pending_review"

    async with AsyncSessionLocal() as session:
        row = (
            await session.execute(select(ConfigModel).where(ConfigModel.id == rec_id))
        ).scalar_one()
        assert isinstance(row.id, UUID)
        assert row.recommendation_type == "parameter_adjustment"
        assert row.status == "pending_review"
        assert row.km_version_analyzed is None or isinstance(
            row.km_version_analyzed, UUID
        )

        audits = (
            await session.execute(
                select(AuditModel).where(AuditModel.recommendation_id == rec_id)
            )
        ).scalars().all()
        assert len(audits) == 1
        assert audits[0].action == "generated"
        assert isinstance(audits[0].id, UUID)
        assert isinstance(audits[0].recommendation_id, UUID)
        assert audits[0].recommendation_id == rec_id