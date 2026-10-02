"""Tests del protocolo de muestreo de OperationalObservation (RFC-006).

Cubre las 4 reglas del alta:
  1. Variación extrema contra la observación anterior -> warning, no rechazo.
  2. Densidad 3x la capacidad declarada            -> warning, no rechazo.
  3. observer_id inválido                          -> 400.
  4. Dos conteos de la misma zona en 15 minutos    -> 400.

Los tests estánPartidos en dos bloques a propósito:

* ``TestQualityRules`` ejercita ``_evaluate_quality``, que es pura y no toca
  la base. Corre en cualquier entorno.
* ``TestObservationProtocol`` va contra la base de verdad. Requiere un Postgres
  con PostGIS funcional, porque ``zones.geometry`` es de tipo Geometry y
  cualquier lectura de esa tabla carga la librería ``postgis-3``. Si el entorno
  no la tiene, los tests se saltan con el motivo en vez de fallar con un error
  de biblioteca que no dice nada del código bajo prueba.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.crud.operational_observation import (
    CAPACITY_MULTIPLE_THRESHOLD,
    MIN_INTERVAL_MINUTES,
    VARIATION_THRESHOLD_PCT,
    WARNING_TYPO,
    WARNING_VARIATION,
    _evaluate_quality,
    _is_valid_uuid,
)

ART = ZoneInfo("America/Argentina/Buenos_Aires")
OBSERVER = "153a712a-1111-2222-3333-444455556666"


# ── 1 y 2. Reglas de calidad (puras, sin base) ───────────────────────────────


class TestQualityRules:
    def test_primera_observacion_no_compara_contra_nada(self):
        """Sin referencia previa no hay variación que evaluar."""
        assert _evaluate_quality(new_density=50, capacity=100, previous_density=None) == {}

    def test_variacion_extrema_marca(self):
        result = _evaluate_quality(new_density=200, capacity=100, previous_density=50)
        assert WARNING_VARIATION in result["warnings"]
        assert result["variacion_pct"] == 300.0
        assert result["densidad_anterior"] == 50

    def test_variacion_en_el_borde_no_marca(self):
        """El umbral es 'mayor que', no 'mayor o igual': 200% exacto no marca."""
        result = _evaluate_quality(new_density=300, capacity=100, previous_density=100)
        assert result == {}

    def test_variacion_justo_por_encima_marca(self):
        result = _evaluate_quality(new_density=301, capacity=100, previous_density=100)
        assert WARNING_VARIATION in result["warnings"]
        assert result["variacion_pct"] == 201.0

    def test_densidad_anterior_cero_no_divide(self):
        """Con 0 previo la variación es indefinida: se salta, no explota."""
        assert _evaluate_quality(new_density=80, capacity=100, previous_density=0) == {}

    def test_supera_capacidad_x3_marca(self):
        result = _evaluate_quality(new_density=400, capacity=100, previous_density=None)
        assert WARNING_TYPO in result["warnings"]
        assert result["capacidad"] == 100
        assert result["densidad_observada"] == 400

    def test_justo_en_el_umbral_de_capacidad_no_marca(self):
        assert (
            _evaluate_quality(
                new_density=100 * CAPACITY_MULTIPLE_THRESHOLD, capacity=100, previous_density=None
            )
            == {}
        )

    def test_capacidad_no_declarada_no_salva_la_regla(self):
        """capacity=0 significa 'no declarada': no se puede afirmar nada."""
        assert _evaluate_quality(new_density=9_999, capacity=0, previous_density=None) == {}

    def test_ambos_warnings_juntos(self):
        result = _evaluate_quality(new_density=400, capacity=100, previous_density=10)
        assert set(result["warnings"]) == {WARNING_VARIATION, WARNING_TYPO}
        assert result["variacion_pct"] == 3900.0
        assert result["capacidad"] == 100

    def test_umbrales_documentados(self):
        """Si alguien cambia un umbral, este test lo vuelve explícito."""
        assert VARIATION_THRESHOLD_PCT == 200.0
        assert CAPACITY_MULTIPLE_THRESHOLD == 3
        assert MIN_INTERVAL_MINUTES == 15


# ── 3. observer_id (puro) ────────────────────────────────────────────────────


class TestObserverIdRule:
    def test_uuid_valido(self):
        assert _is_valid_uuid(OBSERVER)

    def test_uuid_valido_en_mayusculas(self):
        assert _is_valid_uuid(OBSERVER.upper())

    def test_uuid_con_espacios_alrededor(self):
        assert _is_valid_uuid(f"  {OBSERVER}  ")

    @pytest.mark.parametrize(
        "value",
        [
            "invalid-uuid",
            "no-soy-uuid",
            "",
            "   ",
            "153a712a1111222233334444555566",              # sin guiones
            "153a712a-1111-2222-3333-44445555666",         # un caracter corto
            "153a712a-1111-2222-3333-4444555566667",       # un caracter largo
            "153a712a-1111-2222-3333-44445555666g",        # no es hex
            "../../etc/passwd",
        ],
    )
    def test_rechaza_no_uuid(self, value):
        assert not _is_valid_uuid(value)


# ── 1 a 4 contra la base (requiere Postgres con PostGIS funcional) ───────────

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", settings.DATABASE_URL)


def _sync_dsn() -> str:
    import re

    return re.sub(r"^postgresql\+[a-z0-9_]+://", "postgresql://", TEST_DATABASE_URL)


def _require_working_postgres() -> None:
    """Skip si la tabla que este modulo necesita no esta utilizable.

    El guard miraba `zones`, que NO es la tabla que usa el modulo: aqui se escribe
    y lee `operational_observations`. `zones` la crea `tests/conftest.py::test_engine`
    (AppBase) pero `operational_observations` vive en el registro de `src/`
    (InfraBase) y solo la crea `tests/integration/test_recommendation_flow.py`.

    Con el guard sobre `zones` el resultado dependia de que modulo hubiera corrido
    antes en la sesion, y por eso los 6 tests alternaban entre SKIP y ERROR segun
    la corrida: con `zones` presente el guard pasaba y los tests se ejecutaban
    contra una tabla inexistente
    (`asyncpg UndefinedTableError: no existe la relacion
    «operational_observations»`). Guardando la tabla que realmente se usa, el skip
    es determinista y no depende del orden.
    """
    import psycopg2

    try:
        conn = psycopg2.connect(_sync_dsn())
    except Exception as exc:  # pragma: no cover - entorno
        pytest.skip(f"No se pudo abrir la base de tests: {type(exc).__name__}: {exc}")
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, zone_id, observed_density FROM operational_observations LIMIT 1"
            )
    except Exception as exc:  # pragma: no cover - entorno
        conn.close()
        pytest.skip(
            "El entorno no soporta este test: la tabla `operational_observations` "
            f"no es utilizable ({type(exc).__name__}: {str(exc).splitlines()[0]}). "
            "Esa tabla se crea desde el registro de `src/` (tests/integration/"
            "test_recommendation_flow.py::_ensure_test_schema), no desde el "
            "`test_engine` de conftest. No es un fallo del código bajo prueba."
        )
    conn.close()


@pytest.fixture(scope="module")
async def engine():
    _require_working_postgres()
    import re

    # `sslmode` no existe para asyncpg: lo pasa tal cual a `connect()` y revienta
    # con "connect() got an unexpected keyword argument 'sslmode'". Su
    # equivalente es `ssl=`. `_sync_dsn()` solo normaliza el driver, se queda con
    # el `?sslmode=require` de la URL de Neon, asi que hay que traducirlo aqui.
    #
    # Esto estaba latente: con la base de pruebas vacia, `_require_working_postgres`
    # detectaba que `operational_observations` no era utilizable y hacia SKIP de
    # todo el modulo, asi que este fixture nunca llegaba a construirse. En cuanto
    # la tabla existe (base migrada con `alembic upgrade head`, o creada por otro
    # modulo) el guard pasa, el fixture se construye y el error aparece.
    async_url = (
        re.sub(r"^postgresql://", "postgresql+asyncpg://", _sync_dsn())
        .replace("sslmode=require", "ssl=require")
    )
    # `NullPool` por el mismo motivo que en `tests/unit/test_crud_p3.py`: el
    # fixture es de scope "module" pero pytest-asyncio crea un event loop nuevo
    # por test, asi que con pool la segunda sesion reutiliza una conexion creada
    # en el loop del test anterior ("got Future attached to a different loop" /
    # "another operation is in progress").
    engine = create_async_engine(async_url, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine) -> AsyncSession:
    async with engine.connect() as conn:
        tx = await conn.begin()
        maker = async_sessionmaker(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        async with maker() as session:
            yield session
            await session.rollback()
        await tx.rollback()


@pytest.fixture
async def context(session: AsyncSession):
    """Zona y jornada mínimas, con la ventana operativa del día local completo."""
    from app.models.attendance_level import AttendanceLevel
    from app.models.event import Event
    from app.models.event_day import EventDay
    from app.models.operational_profile import OperationalProfile
    from app.models.zone import Zone

    today = datetime.now(ART).date()
    event = Event(id="obs-test-event", name="Censo Test")
    level = AttendanceLevel(
        id="obs-test-level", event_id=event.id, name="Media", min_people=0, max_people=None
    )
    # `event_days.operational_profile_id` es NOT NULL en el esquema que producen
    # las migraciones (`d0e1f2a3b4c5:159`), pero NULLABLE en el modelo
    # (`app/models/event_day.py:30`, que dice estar alineado con `c7d8e9f0a1b2`,
    # migracion que no toca la columna). Con la base de pruebas creada desde
    # `Base.metadata` la columna es nullable y el test pasaba sin esto; contra el
    # esquema real fallaba con `null value in column "operational_profile_id"`.
    # Crear el perfil y referenciarlo deja el test valido contra los dos.
    profile = OperationalProfile(
        # `operational_profiles.id` es UUID en la base (no varchar): un id
        # alfanumerico tipo "obs-test-profile" lo rechaza el driver con
        # "invalid UUID ... length must be between 32..36 characters".
        id=uuid.UUID("0b5c9f14-2d3e-4a6b-8c1f-7e5a9d2b4c60"),
        name="Perfil del test de observaciones",
        description="",
    )
    day = EventDay(
        id="obs-test-day",
        event_id=event.id,
        date=today,
        day_of_week="lunes",
        is_active=True,
        attendance_level_id=level.id,
        operational_profile_id=profile.id,
        operational_start_min=0,
        operational_end_min=1440,
    )
    zone = Zone(
        id="obs-test-zone",
        event_id=event.id,
        name="Baño de Prueba",
        type="bano",
        saturation="bajo",
        status="activa",
        capacity=100,
        available_capacity=100,
    )
    session.add_all([event, level, profile, day, zone])
    await session.flush()
    return zone, day


def _hours_ago(hours: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def _payload(zone, day, density: int, **kwargs):
    from app.schemas.operational_observation import OperationalObservationCreate

    # `timestamp` va por defecto "ahora", pero los tests de la ventana
    # anti-spam lo pasan explicito. Con `**kwargs` al final, un `timestamp` en
    # kwargs llegaba duplicado y reventaba con "got multiple values for keyword
    # argument 'timestamp'". `setdefault` deja que el kwargs gane.
    kwargs.setdefault("timestamp", datetime.now(timezone.utc))
    return OperationalObservationCreate(
        event_day_id=day.id,
        zone_id=zone.id,
        observed_density=density,
        **kwargs,
    )


class TestObservationProtocol:
    @pytest.mark.asyncio
    async def test_observer_id_invalido_rechaza_400(self, session, context):
        from app.crud.operational_observation import create_observation

        zone, day = context
        with pytest.raises(HTTPException) as exc:
            await create_observation(session, _payload(zone, day, 50, observer_id="no-soy-uuid"))
        assert exc.value.status_code == 400
        assert "observer_id inválido" in exc.value.detail

    @pytest.mark.asyncio
    async def test_segunda_observacion_dentro_de_la_ventana_rechaza(self, session, context):
        from app.crud.operational_observation import create_observation

        zone, day = context
        # Las dos observaciones tienen que caer REALMENTE dentro de la ventana de
        # 15 min. Este test usaba 2 h y 1 h, o sea 60 min de diferencia, y aun
        # asi exigia el rechazo: no lo hay, porque la ventana se ancla en el
        # timestamp de la observacion nueva (`since = timestamp - 15 min`), asi
        # que una observacion de hace 2 h queda fuera de la ventana de la de
        # hace 1 h. El codigo de produccion es el correcto; la expectativa del
        # test no. Esto nunca sevio porque el modulo se saltaba entero.
        await create_observation(session, _payload(zone, day, 50, timestamp=_hours_ago(1)))
        with pytest.raises(HTTPException) as exc:
            # 6 minutos despues: dentro de los 15.
            await create_observation(
                session, _payload(zone, day, 60, timestamp=_hours_ago(0.9))
            )
        assert exc.value.status_code == 400
        assert f"menos de {MIN_INTERVAL_MINUTES} minutos" in exc.value.detail

    @pytest.mark.asyncio
    async def test_ventana_permite_carga_retroactiva(self, session, context):
        """La ventana se ancla en el timestamp nuevo, no en 'ahora'.

        Anclarla en now() bloquearía a un operador que completa un censo del
        mediodía, porque la primera observación "de hace 5 horas" ya existiría.
        """
        from app.crud.operational_observation import create_observation

        zone, day = context
        await create_observation(session, _payload(zone, day, 50, timestamp=_hours_ago(5)))
        created = await create_observation(session, _payload(zone, day, 55, timestamp=_hours_ago(2)))
        assert created.id is not None

    @pytest.mark.asyncio
    async def test_warning_llega_a_la_columna_metadata(self, session, context):
        from app.crud.operational_observation import create_observation

        zone, day = context
        created = await create_observation(session, _payload(zone, day, 400))
        assert created.metadata is not None
        assert WARNING_TYPO in created.metadata["warnings"]
        assert created.metadata["capacidad"] == 100

    @pytest.mark.asyncio
    async def test_las_notas_se_conservan(self, session, context):
        """Los warnings se mergean con las notas, no las reemplazan."""
        from app.crud.operational_observation import create_observation

        zone, day = context
        created = await create_observation(
            session, _payload(zone, day, 400, metadata={"notas": "cola larga"})
        )
        assert created.metadata is not None
        assert created.metadata["notas"] == "cola larga"
        assert WARNING_TYPO in created.metadata["warnings"]

    @pytest.mark.asyncio
    async def test_observacion_limpia_no_lleva_warnings(self, session, context):
        from app.crud.operational_observation import create_observation

        zone, day = context
        created = await create_observation(session, _payload(zone, day, 50))
        assert created.metadata is None
