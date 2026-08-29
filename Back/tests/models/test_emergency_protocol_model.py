"""Tests de integridad del modelo EmergencyProtocol (Emergencia V2 - Fase S1).

Verifica el modelo de datos del catálogo de protocolos usando una base SQLite
en memoria y creando únicamente la tabla ``emergency_protocols`` (sin
dependencia de PostGIS ni de la base local/Neon).
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.models.emergency import EmergencyType
from app.models.emergency_protocol import EmergencyProtocol, EmergencyProtocolContext


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[EmergencyProtocol.__table__],
    )
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(
            bind=engine,
            tables=[EmergencyProtocol.__table__],
        )
        engine.dispose()


def _proto(**overrides):
    data = {
        "context": EmergencyProtocolContext.FESTIVAL,
        "title": "Niño perdido",
        "description": "Protocolo para localizar un menor en el festival.",
        "icon": "🧒",
        "steps": [
            "Mantener la calma",
            "Avisar a la policía",
            "Entregar los datos del menor",
        ],
        "priority": 1,
        "order": 0,
        "target_type": EmergencyType.policia,
    }
    data.update(overrides)
    return EmergencyProtocol(**data)


def test_crear_protocolo_valido(db_session):
    p = _proto()
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    assert p.id
    assert p.context == EmergencyProtocolContext.FESTIVAL
    assert p.title == "Niño perdido"
    assert p.description
    assert p.icon == "🧒"
    assert p.priority == 1
    assert p.order == 0
    assert p.target_type == EmergencyType.policia
    assert p.active is True
    assert p.created_at is not None
    assert p.updated_at is not None


def test_unique_context_title(db_session):
    p1 = _proto()
    db_session.add(p1)
    db_session.commit()

    p2 = _proto()
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_same_title_different_context(db_session):
    p1 = _proto(context=EmergencyProtocolContext.FESTIVAL)
    db_session.add(p1)
    db_session.commit()

    p2 = _proto(context=EmergencyProtocolContext.TRANSPORTE)
    db_session.add(p2)
    db_session.commit()
    db_session.refresh(p2)

    assert p2.id != p1.id
    assert p2.title == p1.title
    assert p2.context == EmergencyProtocolContext.TRANSPORTE


def test_priority_valida(db_session):
    for priority in (1, 2, 3):
        p = _proto(title=f"Protocolo prioridad {priority}", priority=priority)
        db_session.add(p)
        db_session.commit()
        db_session.refresh(p)
        assert p.priority == priority


def test_priority_invalida_rechazada(db_session):
    for priority in (0, 4):
        p = _proto(title=f"Protocolo prio {priority}", priority=priority)
        db_session.add(p)
        with pytest.raises(IntegrityError):
            db_session.commit()
        db_session.rollback()


def test_order_no_negativo(db_session):
    p = _proto(order=-1)
    db_session.add(p)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_target_type_nullable(db_session):
    p = _proto(target_type=None)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    assert p.target_type is None


def test_target_type_valido(db_session):
    p = _proto(title="Asalto", target_type=EmergencyType.policia)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    assert p.target_type == EmergencyType.policia


def test_target_type_invalido(db_session):
    p = _proto(target_type="zzz")
    db_session.add(p)
    with pytest.raises((StatementError, LookupError, ValueError, IntegrityError)):
        db_session.commit()
    db_session.rollback()


def test_steps_jsonb(db_session):
    steps = [
        "Primer paso con tilde: evacuar",
        "Segundo paso",
        "Tercer paso",
        "Cuarto paso",
    ]
    p = _proto(steps=steps)
    db_session.add(p)
    db_session.commit()

    stored = db_session.query(EmergencyProtocol).filter(
        EmergencyProtocol.title == "Niño perdido"
    ).one()
    assert isinstance(stored.steps, list)
    assert stored.steps == steps
    assert len(stored.steps) == 4
    assert stored.steps[0] == "Primer paso con tilde: evacuar"


def test_default_active_true(db_session):
    p = _proto(active=True)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)

    assert p.active is True