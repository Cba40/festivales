"""Tests de integridad del modelo de Emergencia V1 (S1).

Verifica el modelo de datos (City + Emergency) usando una base SQLite en
memoria y creando únicamente las tablas ``cities`` y ``emergencies`` (sin
dependencia de PostGIS ni de la base local/Neon).
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.models.city import City
from app.models.emergency import Emergency, EmergencyType


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        bind=engine,
        tables=[City.__table__, Emergency.__table__],
    )
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(
            bind=engine,
            tables=[City.__table__, Emergency.__table__],
        )
        engine.dispose()


@pytest.fixture
def sample_city(db_session) -> City:
    city = City(name="Jesús María", province="Córdoba", country="Argentina")
    db_session.add(city)
    db_session.commit()
    db_session.refresh(city)
    return city


def test_crear_ciudad(db_session):
    city = City(name="Córdoba", province="Córdoba", country="Argentina")
    db_session.add(city)
    db_session.commit()
    db_session.refresh(city)

    assert city.id
    assert city.name == "Córdoba"
    assert city.province == "Córdoba"
    assert city.country == "Argentina"


def test_crear_emergencia_vinculada_a_ciudad(db_session, sample_city):
    em = Emergency(
        city_id=sample_city.id,
        name="Hospital Municipal",
        type=EmergencyType.salud,
        phone="+54 3525 421234",
        emergency_number="107",
        latitude=-30.9815,
        longitude=-64.0920,
        services="Urgencias, guardia 24hs",
        schedule="24hs",
    )
    db_session.add(em)
    db_session.commit()
    db_session.refresh(em)

    assert em.id
    assert em.city_id == sample_city.id
    assert em.name == "Hospital Municipal"
    assert em.type == EmergencyType.salud


def test_enum_acepta_valores_correctos():
    assert EmergencyType("policia") == EmergencyType.policia
    assert EmergencyType("bomberos") == EmergencyType.bomberos
    assert EmergencyType("salud") == EmergencyType.salud
    assert EmergencyType("defensa_civil") == EmergencyType.defensa_civil
    assert EmergencyType("numero_emergencia") == EmergencyType.numero_emergencia
    assert EmergencyType("otro") == EmergencyType.otro


def test_enum_rechaza_valores_invalidos():
    with pytest.raises(ValueError):
        EmergencyType("invalid")
    with pytest.raises(ValueError):
        EmergencyType("firefighters")


def test_unique_city_name(db_session, sample_city):
    em1 = Emergency(
        city_id=sample_city.id,
        name="Cuartel Bomberos Voluntarios",
        type=EmergencyType.bomberos,
    )
    db_session.add(em1)
    db_session.commit()

    em2 = Emergency(
        city_id=sample_city.id,
        name="Cuartel Bomberos Voluntarios",
        type=EmergencyType.bomberos,
    )
    db_session.add(em2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_lat_long_pueden_ser_null_para_numero_emergencia(db_session, sample_city):
    em = Emergency(
        city_id=sample_city.id,
        name="Emergencias 911",
        type=EmergencyType.numero_emergencia,
        emergency_number="911",
        services="Número único de emergencias",
        schedule="24hs",
    )
    db_session.add(em)
    db_session.commit()
    db_session.refresh(em)

    assert em.latitude is None
    assert em.longitude is None


def test_relacion_city_emergencies_1n(db_session, sample_city):
    e1 = Emergency(city_id=sample_city.id, name="E1", type=EmergencyType.policia)
    e2 = Emergency(city_id=sample_city.id, name="E2", type=EmergencyType.bomberos)
    db_session.add_all([e1, e2])
    db_session.commit()

    db_session.refresh(sample_city)
    names = {e.name for e in sample_city.emergencies}
    assert names == {"E1", "E2"}
    assert len(sample_city.emergencies) == 2
