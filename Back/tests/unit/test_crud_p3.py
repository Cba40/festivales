"""Tests unitarios de CRUD P3.0 — integridad referencial, unicidad, validaciones.

Cubre §13: unicidad de nombre, clave compuesta, FK validation, filtro de eventos activos.
"""
import os
import uuid

import pytest
from sqlalchemy import DefaultClause, String, create_engine, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.crud import (
    create_event_day,
    create_event_day_phase,
    create_operational_event,
    create_operational_phase,
    create_operational_profile,
    create_zone_behavior,
    get_operational_event,
    list_events_by_event_day,
    list_phases_by_profile,
    list_phases_by_event_day,
    update_event_day,
    update_event_day_phase,
    update_operational_profile,
    update_operational_phase,
)
from app.crud.zone_type import zone_type as zone_type_crud
from app.db.session import Base
from app.schemas.event_day import EventDayCreate, EventDayUpdate
from app.services.zone_behavior_sync import sync_zone_behaviors
from app.schemas.event_day_phase import EventDayPhaseUpdate
from app.schemas.operational_event import OperationalEventCreate
from app.schemas.operational_phase import OperationalPhaseCreate
from app.schemas.operational_profile import OperationalProfileCreate
from app.schemas.zone_behavior import ZoneBehaviorCreate
from app.models.event_day_phase import EventDayPhase
from app.models.zone import Zone
from app.schemas.zone_type import ZoneTypeCreate

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", settings.DATABASE_URL)


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def async_engine():
    async_url = TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(async_url)
    return engine


@pytest.fixture(scope="session", autouse=True)
def _degrade_geometry_columns():
    """Baja a `String` todas las columnas `geometry` del metadata de `app/`.

    El entorno local no tiene PostGIS: no esta en `pg_available_extensions`,
    `CREATE EXTENSION postgis` falla y no hay binarios en disco. Sin la
    extension, `create_all` falla con
    `UndefinedFile: no se pudo acceder al archivo «postgis-3»`, y un `SELECT` que
    proyecte la columna muere en `ST_AsEWKB`.

    No es solo `zones.geometry`: tambien la declara `events.geometry`
    (POLYGON) y `points.geometry` (POINT). Se recorren todas, asi que este
    parche no depende de cual tabla cree `create_all` primero.

    Estos tests nunca usan la geometria: solo leen `zone.id` y `zone.capacity`.
    Hay que tocar el tipo y no solo el DDL porque el problema esta en la
    expresion del SELECT, no en la definicion de la tabla.

    Es el mismo patron que ya usan `test_operational_observations.py` y
    `test_recommendation_flow.py`.
    """
    saved = [
        (table.c[column_name], column.type)
        for table in Base.metadata.tables.values()
        for column_name, column in table.columns.items()
        if "geometry" in column.type.__class__.__name__.lower()
    ]
    for column, _ in saved:
        column.type = String()

    # Los indices GIST sobre esas columnas tambien fallan sin PostGIS: ahora la
    # columna es VARCHAR, y `USING gist` exige una clase de operadores por omision
    # para el tipo. Se quitan del metadata mientras corre el modulo (se restauran
    # al terminar). No los usa ningun test de aqui.
    removed_indexes = [
        index for table in Base.metadata.tables.values() for index in table.indexes
        if "geometry" in [c.name for c in index.columns]
    ]
    for index in removed_indexes:
        index.table.indexes.discard(index)

    # Segundo bug pre-existente de los modelos: `EventDayPhase.intensity` declara
    # `server_default=func.text('1.0')`, y Postgres rechaza un default de tipo
    # `text` sobre una columna `double precision` (DatatypeMismatch). Se corrige
    # solo para el DDL de este modulo, sin tocar `app/`. Mismo workaround que ya
    # aplica `tests/integration/test_recommendation_flow.py`.
    intensity_column = EventDayPhase.__table__.c.intensity
    saved_default = intensity_column.server_default
    intensity_column.server_default = DefaultClause(text("1.0"))

    try:
        yield
    finally:
        intensity_column.server_default = saved_default
        for column, original_type in saved:
            column.type = original_type
        for index in removed_indexes:
            index.table.indexes.add(index)


@pytest.fixture
async def async_session(async_engine) -> AsyncSession:
    """Sesion asincrona transaccional, con la misma politica que produccion.

    `expire_on_commit=False` es obligatorio y no es cosmetico: TODOS los CRUD de
    `app/crud/` terminan en `await db.commit()`. Con el default de SQLAlchemy
    (`True`), ese commit expira **todos** los objetos vivos en la sesion, y el
    siguiente acceso a un atributo (`prof.id`, `profile_a.id`) dispara una carga
    perezosa fuera del contexto greenlet -> `sqlalchemy.exc.MissingGreenlet`.
    La app real ya lo hace asi en `src/infrastructure/db/config.py:24`.

    `join_transaction_mode="create_savepoint"` hace que el `commit()` de cada CRUD
    libere un SAVEPOINT en vez de la transaccion externa, de modo que el
    `rollback()` del fixture seguiria revirtiendo todo. Es el mismo criterio que
    usa `tests/crud/test_operational_observation.py:181` y que ya documenta el
    fixture `sync_session` de este modulo.
    """
    async with async_engine.connect() as conn:
        tx = await conn.begin()
        maker = async_sessionmaker(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        async with maker() as session:
            yield session
            await session.rollback()
        await tx.rollback()


@pytest.fixture
async def clean_tables(async_engine):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture
async def seed_zone_types(async_session: AsyncSession):
    from app.models.zone_type import ZoneType

    rows = [
        ("zt-estacionamiento", "Estacionamiento", "estacionamiento", "car"),
        ("zt-gastronomia", "Gastronomía", "gastronomia", "utensils-crossed"),
        ("zt-transporte", "Transporte", "transporte", "bus"),
        ("zt-sanitarios", "Sanitarios", "sanitarios", "toilet"),
        ("zt-seguridad", "Seguridad", "seguridad", "shield"),
    ]
    for zt_id, name, slug, icon in rows:
        existing = await async_session.get(ZoneType, zt_id)
        if not existing:
            async_session.add(ZoneType(
                id=zt_id, name=name, slug=slug, icon=icon, description=name,
                default_factors={"saturation": 1.0, "attendance": 1.0, "resource": 1.0},
            ))
    await async_session.flush()


@pytest.fixture
async def seed_profile(async_session: AsyncSession):
    from app.models.operational_profile import OperationalProfile

    existing = await async_session.execute(
        text("SELECT id FROM operational_profiles WHERE name = 'TestProfile'")
    )
    row = existing.scalar_one_or_none()
    if row:
        return row

    prof = OperationalProfile(name="TestProfile", description="")
    async_session.add(prof)
    await async_session.flush()
    await async_session.refresh(prof)
    return prof.id


@pytest.fixture
async def seed_profile_and_phase(async_session: AsyncSession, seed_profile):
    profile_id = seed_profile
    try:
        phase = await create_operational_phase(
            async_session,
            OperationalPhaseCreate(
                operational_profile_id=profile_id,
                name="FaseTest",
                sort_order=1,
            ),
        )
        return profile_id, phase.id
    except ValueError:
        phases = await list_phases_by_profile(async_session, profile_id)
        return profile_id, phases[0].id


# ── Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
class TestOperationalProfileCRUD:

    async def test_operational_profile_name_uniqueness(
        self, async_session: AsyncSession, clean_tables,
    ):
        """§13: Crear dos perfiles con mismo name → ValueError en el segundo."""
        await create_operational_profile(
            async_session, OperationalProfileCreate(name="ProfileUnico", description=""),
        )
        with pytest.raises(ValueError) as exc_info:
            await create_operational_profile(
                async_session, OperationalProfileCreate(name="ProfileUnico", description=""),
            )
        assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
class TestOperationalPhaseCRUD:

    async def test_operational_phase_sort_order_uniqueness_per_profile(
        self, async_session: AsyncSession, seed_profile, clean_tables,
    ):
        """§13: Crear dos fases con mismo sort_order en mismo perfil → ValueError."""
        profile_id = seed_profile
        await create_operational_phase(
            async_session,
            OperationalPhaseCreate(
                operational_profile_id=profile_id,
                name="Fase1",
                sort_order=1,
            ),
        )
        with pytest.raises(ValueError) as exc_info:
            await create_operational_phase(
                async_session,
                OperationalPhaseCreate(
                    operational_profile_id=profile_id,
                    name="Fase2",
                    sort_order=1,
                ),
            )
        assert "sort_order" in str(exc_info.value).lower() or "already exists" in str(exc_info.value)


@pytest.mark.asyncio
class TestZoneBehaviorCRUD:

    async def test_zone_behavior_composite_key_uniqueness(
        self, async_session: AsyncSession, seed_profile, seed_zone_types, clean_tables,
    ):
        """P3.1A: la fase auto-genera el ZoneBehavior; replicar (phase_id, zone_type_id) → ValueError."""
        profile_id = seed_profile
        phase = await create_operational_phase(
            async_session,
            OperationalPhaseCreate(
                operational_profile_id=profile_id,
                name="FaseUniqueness",
                sort_order=70,
            ),
        )
        # seed_zone_types se ejecutó antes que esta llamada: la fase ya tiene
        # auto-generados sus ZoneBehavior para todos los ZoneType seedeados.
        zt_id = "zt-estacionamiento"
        with pytest.raises(ValueError) as exc_info:
            await create_zone_behavior(
                async_session,
                ZoneBehaviorCreate(
                    operational_phase_id=phase.id,
                    zone_type_id=zt_id,
                    saturation_factor=2.0,
                    availability_factor=2.0,
                    resource_factor=2.0,
                    priority_weight=2.0,
                ),
            )
        assert "already exists" in str(exc_info.value)

    async def test_zone_behavior_requires_existing_phase_and_zone_type(
        self, async_session: AsyncSession, clean_tables,
    ):
        """§13: Crear ZoneBehavior con phase_id o zone_type_id inexistente → ValueError."""
        fake_phase_id = uuid.uuid4()
        fake_zt_id = str(uuid.uuid4())

        with pytest.raises(ValueError) as exc_info:
            await create_zone_behavior(
                async_session,
                ZoneBehaviorCreate(
                    operational_phase_id=fake_phase_id,
                    zone_type_id=fake_zt_id,
                    saturation_factor=1.0,
                    availability_factor=1.0,
                    resource_factor=1.0,
                    priority_weight=1.0,
                ),
            )
        assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
class TestOperationalEventCRUD:

    @pytest.mark.skip(
        reason="CRUD V1 (RFC): list_active_by_event_day legacy eliminado con start_min/end_min"
    )
    async def test_list_active_by_event_day_filters_correctly(
        self, async_session: AsyncSession, clean_tables,
    ):
        """§13: Solo retorna eventos activos y vigentes para current_min."""
        from app.models.attendance_level import AttendanceLevel
        from app.models.event import Event
        from app.models.event_day import EventDay

        event = Event(id="test-event-crud-filter", name="Filter Test", description="")
        async_session.add(event)
        await async_session.flush()

        al = AttendanceLevel(id="al-filter-test", event_id=event.id, name="TestAL",
                             min_people=0, max_people=100000)
        async_session.add(al)
        await async_session.flush()

        from app.models.operational_profile import OperationalProfile
        prof = OperationalProfile(name="FilterProfile", description="")
        async_session.add(prof)
        await async_session.flush()

        day = EventDay(
            id="test-ed-active-filter",
            event_id=event.id,
            date="2026-07-10",
            day_of_week="jueves",
            operational_profile_id=prof.id,
            operational_start_min=480,
            operational_end_min=1800,
            attendance_level_id=al.id,
            is_active=True,
        )
        async_session.add(day)
        await async_session.flush()

        e1 = await create_operational_event(
            async_session,
            OperationalEventCreate(
                event_day_id="test-ed-active-filter",
                event_type="tormenta",
                description="Tormenta eléctrica",
                start_min=0,
                end_min=1000,
                is_active=True,
            ),
        )

        await create_operational_event(
            async_session,
            OperationalEventCreate(
                event_day_id="test-ed-active-filter",
                event_type="fin_espectaculo",
                description="Fin del show principal",
                start_min=0,
                end_min=200,
                is_active=True,
            ),
        )

        await create_operational_event(
            async_session,
            OperationalEventCreate(
                event_day_id="test-ed-active-filter",
                event_type="corte_energia",
                description="Corte programado",
                start_min=0,
                end_min=1000,
                is_active=False,
            ),
        )

        active = await list_active_by_event_day(async_session, "test-ed-active-filter", 500)
        assert len(active) == 1
        assert active[0].id == e1.id


@pytest.mark.asyncio
class TestEventDayCRUD:

    async def test_event_day_create_validates_operational_window(
        self, async_session: AsyncSession, clean_tables,
    ):
        """§13: Ventana operacional invertida (`end_min <= start_min`) → ValueError."""
        from app.models.attendance_level import AttendanceLevel
        from app.models.event import Event

        event = Event(id="test-event-crud-al", name="AL Test", description="")
        async_session.add(event)
        al = AttendanceLevel(id="al-crud-test", event_id=event.id, name="TestAL",
                             min_people=0, max_people=100000)
        async_session.add(al)
        await async_session.flush()

        with pytest.raises(ValueError) as exc_info:
            await create_event_day(
                async_session,
                EventDayCreate(
                    date="2026-07-10",
                    day_of_week="jueves",
                    operational_start_min=1800,
                    operational_end_min=480,
                    attendance_level_id=al.id,
                ),
                event_id="test-event-crud-al",
            )
        assert "operational_end_min" in str(exc_info.value)

    async def test_event_day_create_missing_profile_violates_foreign_key(
        self, async_session: AsyncSession, clean_tables,
    ):
        """§13: `operational_profile_id` inexistente lo detiene la FK de Postgres.

        RFC-007 elimino el chequeo en CRUD (`create` ya no hace
        `db.get(OperationalProfile, ...)`) y declaro `OperationalProfile` como
        entidad de compatibilidad. La integridad referencial la garantiza la FK
        `event_days_operational_profile_id_fkey`, no una validacion previa, asi que
        lo que se observa es un `IntegrityError` de SQLAlchemy, no un `ValueError`.
        """
        from sqlalchemy.exc import IntegrityError

        from app.models.attendance_level import AttendanceLevel
        from app.models.event import Event

        event = Event(id="test-event-crud-al", name="AL Test", description="")
        async_session.add(event)
        al = AttendanceLevel(id="al-crud-test", event_id=event.id, name="TestAL",
                             min_people=0, max_people=100000)
        async_session.add(al)
        await async_session.flush()

        fake_profile_id = uuid.uuid4()
        with pytest.raises(IntegrityError) as exc_info:
            await create_event_day(
                async_session,
                EventDayCreate(
                    date="2026-07-10",
                    day_of_week="jueves",
                    operational_profile_id=fake_profile_id,
                    operational_start_min=480,
                    operational_end_min=1800,
                    attendance_level_id=al.id,
                ),
                event_id="test-event-crud-al",
            )
        assert "event_days_operational_profile_id_fkey" in str(exc_info.value)


@pytest.mark.asyncio
class TestEventDayPhaseCRUD:

    async def _setup_phase(self, async_session: AsyncSession):
        from app.models.attendance_level import AttendanceLevel
        from app.models.event import Event
        from app.models.event_day import EventDay
        from app.models.operational_profile import OperationalProfile
        from app.schemas.event_day_phase import EventDayPhaseCreate

        event = Event(id="test-edp-event", name="EDP Test", description="")
        async_session.add(event)
        prof = OperationalProfile(name="EDPProfile", description="")
        async_session.add(prof)
        al = AttendanceLevel(id="al-edp-test", event_id=event.id, name="EDPAL",
                             min_people=0, max_people=100000)
        async_session.add(al)
        await async_session.flush()

        day = EventDay(
            id="test-edp-day",
            event_id=event.id,
            date="2026-08-01",
            day_of_week="sabado",
            operational_profile_id=prof.id,
            operational_start_min=480,
            operational_end_min=1800,
            attendance_level_id=al.id,
            is_active=True,
        )
        async_session.add(day)
        await async_session.flush()

        p1 = await create_operational_phase(
            async_session,
            OperationalPhaseCreate(
                operational_profile_id=prof.id,
                name="EDP Fase1",
                sort_order=1,
            ),
        )
        p2 = await create_operational_phase(
            async_session,
            OperationalPhaseCreate(
                operational_profile_id=prof.id,
                name="EDP Fase2",
                sort_order=2,
            ),
        )

        edp = await create_event_day_phase(
            async_session,
            day.id,
            EventDayPhaseCreate(
                operational_phase_id=p1.id,
                start_min=480,
                end_min=600,
                intensity=1.0,
            ),
        )
        return edp, p2.id

    async def test_update_with_valid_operational_phase(
        self, async_session: AsyncSession, clean_tables,
    ):
        """§13: Actualizar operational_phase_id con fase existente → OK."""
        edp, p2_id = await self._setup_phase(async_session)
        updated = await update_event_day_phase(
            async_session, edp,
            EventDayPhaseUpdate(operational_phase_id=p2_id),
        )
        assert updated.operational_phase_id == p2_id

    async def test_update_with_invalid_operational_phase(
        self, async_session: AsyncSession, clean_tables,
    ):
        """§13: Actualizar operational_phase_id con fase inexistente → ValueError."""
        edp, _ = await self._setup_phase(async_session)
        fake_id = uuid.uuid4()
        with pytest.raises(ValueError) as exc_info:
            await update_event_day_phase(
                async_session, edp,
                EventDayPhaseUpdate(operational_phase_id=fake_id),
            )
        assert "not found" in str(exc_info.value).lower()


@pytest.fixture
def sync_session():
    """Sesión síncrona transaccional: el commit del CRUD solo libera el SAVEPOINT."""
    sync_engine = create_engine(TEST_DATABASE_URL)
    connection = sync_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    session.begin_nested()
    yield session
    session.close()
    transaction.rollback()
    connection.close()
    sync_engine.dispose()


# Sin `@pytest.mark.asyncio`: `pytest.ini` ya fija `asyncio_mode = auto`, asi que
# pytest-asyncio recognise solo los tests y fixtures asincronos. Ademas esta clase
# mezcla un test sincrono sobre `sync_session` (el CRUD de `zone_type.create` es
# sincrono), que bajo el marcador de clase emitia
# `PytestWarning: marked with '@pytest.mark.asyncio' but it is not an async function`.
class TestIntegrityP31A:
    """P3.1A — Integridad del modelo operacional (comportamientos automáticos)."""

    async def test_create_operational_phase_creates_behavior_for_each_zone_type(
        self, async_session: AsyncSession, seed_zone_types, clean_tables,
    ):
        """Al crear una OperationalPhase se crea un ZoneBehavior para CADA ZoneType."""
        from app.models.operational_profile import OperationalProfile
        from app.models.zone_behavior import ZoneBehavior

        profile = await create_operational_profile(
            async_session, OperationalProfileCreate(name="P31A-Fase-ZT", description=""),
        )
        phase = await create_operational_phase(
            async_session,
            OperationalPhaseCreate(
                operational_profile_id=profile.id,
                name="FaseP31A",
                sort_order=1,
            ),
        )

        behaviors = (
            await async_session.execute(
                select(ZoneBehavior).where(ZoneBehavior.operational_phase_id == phase.id)
            )
        ).scalars().all()
        # seed_zone_types crea 5 ZoneTypes → la fase debe tener 5 comportamientos
        assert len(behaviors) == 5
        for behavior in behaviors:
            assert float(behavior.saturation_factor) == 1.0
            assert float(behavior.availability_factor) == 1.0
            assert float(behavior.resource_factor) == 1.0
            assert float(behavior.priority_weight) == 1.0
            assert behavior.density_factor == 0.5
            assert behavior.flow_restriction == "OPEN"

    def test_create_zone_type_creates_behavior_for_each_phase(
        self, sync_session: Session,
    ):
        """Al crear un nuevo ZoneType se crea un ZoneBehavior para TODAS las fases."""
        from app.models.operational_phase import OperationalPhase
        from app.models.operational_profile import OperationalProfile
        from app.models.zone_behavior import ZoneBehavior

        profile = OperationalProfile(name="P31A-ZoneType", description="")
        sync_session.add(profile)
        sync_session.flush()

        p1 = OperationalPhase(operational_profile_id=profile.id, name="F1", sort_order=1)
        p2 = OperationalPhase(operational_profile_id=profile.id, name="F2", sort_order=2)
        sync_session.add_all([p1, p2])
        sync_session.flush()
        phase_ids = {p1.id, p2.id}

        zt = zone_type_crud.create(
            sync_session,
            ZoneTypeCreate(
                name="NuevoTipoP31A",
                slug="nuevo_tipo_p31a",
                icon="x",
                description="test",
                default_factors={"saturation": 1.0},
            ),
        )

        behaviors = (
            sync_session.execute(
                select(ZoneBehavior).where(ZoneBehavior.zone_type_id == zt.id)
            )
        ).scalars().all()
        assert len(behaviors) == 2
        assert {b.operational_phase_id for b in behaviors} == phase_ids
        for behavior in behaviors:
            assert float(behavior.saturation_factor) == 1.0
            assert behavior.density_factor == 0.5
            assert behavior.flow_restriction == "OPEN"

    async def test_rollback_when_behavior_creation_fails(
        self, async_session: AsyncSession, seed_zone_types, clean_tables,
    ):
        """Si la creación automática falla → rollback completo, sin datos parciales."""
        from unittest.mock import patch

        from app.models.operational_phase import OperationalPhase

        # `seed_zone_types` es imprescindible, no decorativo: `sync_zone_behaviors`
        # devuelve 0 sin ningun ZoneType que sincronizar
        # (`zone_behavior_sync.py:77`), sin llamar nunca a `default_behavior`. Sin al
        # menos un ZoneType el parche no se disparaba y el test terminaba en
        # `DID NOT RAISE`.
        profile = await create_operational_profile(
            async_session, OperationalProfileCreate(name="P31A-Rollback", description=""),
        )

        with patch(
            "app.services.zone_behavior_sync.default_behavior",
            side_effect=RuntimeError("boom"),
        ):
            with pytest.raises(RuntimeError):
                await create_operational_phase(
                    async_session,
                    OperationalPhaseCreate(
                        operational_profile_id=profile.id,
                        name="FaseRollback",
                        sort_order=1,
                    ),
                )

        result = await async_session.execute(
            select(OperationalPhase).where(OperationalPhase.name == "FaseRollback")
        )
        assert result.scalar_one_or_none() is None


class TestZoneBehaviorSyncP31B:
    """P3.1B — Sincronización automática e idempotente de ZoneBehavior."""

    def _add_zone_types(self, session: Session, slugs: list[str]):
        from app.models.zone_type import ZoneType

        types = []
        for slug in slugs:
            zt = ZoneType(
                id=f"zt-p31b-{slug}",
                name=slug,
                slug=slug,
                icon="x",
                description="test",
                default_factors={},
            )
            session.add(zt)
            types.append(zt)
        session.flush()
        return types

    def _add_phase(self, session: Session, profile_id, name: str, sort_order: int):
        from app.models.operational_phase import OperationalPhase

        phase = OperationalPhase(
            operational_profile_id=profile_id, name=name, sort_order=sort_order,
        )
        session.add(phase)
        session.flush()
        return phase

    def _combos(self, session: Session) -> set:
        from app.models.zone_behavior import ZoneBehavior

        rows = session.execute(
            select(ZoneBehavior.operational_phase_id, ZoneBehavior.zone_type_id)
        ).all()
        return {(r[0], r[1]) for r in rows}

    def test_old_phase_without_behaviors_gets_missing(self, sync_session: Session):
        """Fase antigua sin ZoneBehavior recibe automáticamente los faltantes."""
        from app.models.operational_profile import OperationalProfile
        from app.models.zone_behavior import ZoneBehavior

        types = self._add_zone_types(sync_session, ["a", "b"])
        profile = OperationalProfile(name="P31B-FaseAntigua", description="")
        sync_session.add(profile)
        sync_session.flush()
        phase = self._add_phase(sync_session, profile.id, "FaseAntigua", 1)

        created = sync_zone_behaviors(sync_session, phase_ids=[phase.id])
        assert created == len(types)

        behaviors = sync_session.execute(
            select(ZoneBehavior).where(ZoneBehavior.operational_phase_id == phase.id)
        ).scalars().all()
        assert len(behaviors) == len(types)
        for behavior in behaviors:
            assert float(behavior.saturation_factor) == 1.0
            assert behavior.density_factor == 0.5
            assert behavior.flow_restriction == "OPEN"

    def test_complete_phase_no_duplicates(self, sync_session: Session):
        """Fase completa: re-sincronizar no genera duplicados."""
        from app.models.operational_profile import OperationalProfile

        types = self._add_zone_types(sync_session, ["a", "b"])
        profile = OperationalProfile(name="P31B-FaseCompleta", description="")
        sync_session.add(profile)
        sync_session.flush()
        phase = self._add_phase(sync_session, profile.id, "FaseCompleta", 1)

        sync_zone_behaviors(sync_session, phase_ids=[phase.id])
        combos_after_first = self._combos(sync_session)

        created_second = sync_zone_behaviors(sync_session, phase_ids=[phase.id])
        assert created_second == 0
        assert self._combos(sync_session) == combos_after_first
        assert len(types) == 2

    def test_new_zone_type_completes_only_missing(self, sync_session: Session):
        """Nuevo ZoneType completa únicamente las combinaciones faltantes."""
        from app.models.operational_profile import OperationalProfile
        from app.models.zone_behavior import ZoneBehavior

        existing_type = self._add_zone_types(sync_session, ["a"])[0]
        profile = OperationalProfile(name="P31B-NuevoTipo", description="")
        sync_session.add(profile)
        sync_session.flush()
        phase = self._add_phase(sync_session, profile.id, "Fase1", 1)

        sync_zone_behaviors(sync_session, phase_ids=[phase.id])
        combos_before = self._combos(sync_session)
        assert combos_before == {(phase.id, existing_type.id)}

        new_type = self._add_zone_types(sync_session, ["nuevo"])[0]
        created = sync_zone_behaviors(sync_session, zone_type_ids=[new_type.id])
        assert created == 1

        combos_after = self._combos(sync_session)
        assert combos_after == {
            (phase.id, existing_type.id),
            (phase.id, new_type.id),
        }
        behaviors = sync_session.execute(
            select(ZoneBehavior).where(ZoneBehavior.zone_type_id == new_type.id)
        ).scalars().all()
        assert len(behaviors) == 1
        for behavior in behaviors:
            assert behavior.density_factor == 0.5
            assert behavior.flow_restriction == "OPEN"

    def test_sync_twice_produces_same_result(self, sync_session: Session):
        """Ejecutar la sincronización dos veces produce exactamente el mismo resultado."""
        from app.models.operational_profile import OperationalProfile

        types = self._add_zone_types(sync_session, ["a", "b", "c"])
        profile = OperationalProfile(name="P31B-Idempotente", description="")
        sync_session.add(profile)
        sync_session.flush()
        self._add_phase(sync_session, profile.id, "F1", 1)
        self._add_phase(sync_session, profile.id, "F2", 2)

        first = sync_zone_behaviors(sync_session)
        combos_first = self._combos(sync_session)
        total_first = len(combos_first)

        second = sync_zone_behaviors(sync_session)
        combos_second = self._combos(sync_session)

        assert second == 0
        assert combos_second == combos_first
        assert len(combos_second) == total_first
        assert total_first == 2 * len(types)


@pytest.mark.asyncio
class TestEventDayProfileIntegrityP31C:
    """P3.1C — Independencia de las fases del EventDay respecto a su perfil.

    Este bloque se reescribio sobre el contrato vigente. La version anterior
    exigia que toda EventDayPhase perteneciera al mismo OperationalProfile que su
    EventDay ("does not belong"), una invariante que RFC-007 elimino a proposito
    (`alear modelo persistente con RFC-007`):

      - RFC-007, seccion 4.4: "Una vez configurada una jornada, sus fases son
        independientes del perfil que las origino: modificaciones posteriores en
        OperationalProfile no afectan las fases ya configuradas".
      - El commit que alineo el modelo con RFC-007 elimino de
        `app/crud/event_day.py` y `app/crud/event_day_phase.py` los chequeos
        `does not belong to OperationalProfile` y `operational_profile_id cannot
        change without providing new 'phases'`.

    Los tests de aqui ahora fijan el comportamiento real: el perfil organiza fases
    al configurar la jornada y despues deja de intervenir. Lo que si se sigue
    validando es la existencia de la `OperationalPhase` referenciada, que si forma
    parte del contrato.
    """

    async def _setup(self, async_session: AsyncSession):
        from app.models.attendance_level import AttendanceLevel
        from app.models.event import Event

        event = Event(id="test-p31c-event", name="P31C Event", description="")
        async_session.add(event)
        al = AttendanceLevel(
            id="al-p31c", event_id=event.id, name="P31C AL",
            min_people=0, max_people=100000,
        )
        async_session.add(al)
        await async_session.flush()

        profile_a = await create_operational_profile(
            async_session, OperationalProfileCreate(name="P31C-ProfA", description=""),
        )
        profile_b = await create_operational_profile(
            async_session, OperationalProfileCreate(name="P31C-ProfB", description=""),
        )
        phase_a = await create_operational_phase(
            async_session,
            OperationalPhaseCreate(
                operational_profile_id=profile_a.id, name="P31C A1", sort_order=1,
            ),
        )
        phase_b = await create_operational_phase(
            async_session,
            OperationalPhaseCreate(
                operational_profile_id=profile_b.id, name="P31C B1", sort_order=1,
            ),
        )
        return event.id, al.id, profile_a.id, profile_b.id, phase_a.id, phase_b.id

    async def _make_day(
        self, async_session: AsyncSession, event_id, al_id, profile_id, phase_ids,
    ):
        from app.schemas.event_day_phase import EventDayPhaseCreate

        return await create_event_day(
            async_session,
            EventDayCreate(
                date="2026-09-01",
                day_of_week="martes",
                operational_profile_id=profile_id,
                operational_start_min=0,
                operational_end_min=600,
                attendance_level_id=al_id,
                phases=[
                    EventDayPhaseCreate(
                        operational_phase_id=ph, start_min=0, end_min=300, intensity=1.0,
                    )
                    for ph in phase_ids
                ],
            ),
            event_id=event_id,
        )

    async def test_create_accepts_phase_from_other_profile(
        self, async_session: AsyncSession, clean_tables,
    ):
        """RFC-007 §4.4: un EventDay puede traer una fase creada en otro perfil."""
        from app.schemas.event_day_phase import EventDayPhaseCreate

        e, al, pa, _pb, _pha, phb = await self._setup(async_session)
        day = await create_event_day(
            async_session,
            EventDayCreate(
                date="2026-06-02",
                day_of_week="miercoles",
                operational_profile_id=pa,
                operational_start_min=0,
                operational_end_min=600,
                attendance_level_id=al,
                phases=[
                    EventDayPhaseCreate(
                        operational_phase_id=phb, start_min=0, end_min=300, intensity=1.0,
                    )
                ],
            ),
            event_id=e,
        )

        assert day.operational_profile_id == pa
        phases = await list_phases_by_event_day(async_session, day.id)
        assert [p.operational_phase_id for p in phases] == [phb]

    async def test_create_rejects_unknown_operational_phase(
        self, async_session: AsyncSession, clean_tables,
    ):
        """Una OperationalPhase inexistente si se rechaza: ese chequeo sigue vigente."""
        from app.schemas.event_day_phase import EventDayPhaseCreate

        e, al, pa, _pb, _pha, _phb = await self._setup(async_session)
        with pytest.raises(ValueError) as exc_info:
            await create_event_day(
                async_session,
                EventDayCreate(
                    date="2026-06-02",
                    day_of_week="miercoles",
                    operational_profile_id=pa,
                    operational_start_min=0,
                    operational_end_min=600,
                    attendance_level_id=al,
                    phases=[
                        EventDayPhaseCreate(
                            operational_phase_id=uuid.uuid4(),
                            start_min=0,
                            end_min=300,
                            intensity=1.0,
                        )
                    ],
                ),
                event_id=e,
            )
        assert "not found" in str(exc_info.value).lower()

    async def test_update_keeps_phases_when_profile_changes(
        self, async_session: AsyncSession, clean_tables,
    ):
        """RFC-007 §4.4: cambiar el perfil sin mandar fases conserva las existentes."""
        e, al, pa, pb, pha, _phb = await self._setup(async_session)
        day = await self._make_day(async_session, e, al, pa, [pha])

        updated = await update_event_day(
            async_session, day, EventDayUpdate(operational_profile_id=pb),
        )

        assert updated.operational_profile_id == pb
        phases = await list_phases_by_event_day(async_session, day.id)
        assert [p.operational_phase_id for p in phases] == [pha]

    async def test_update_accepts_phases_from_another_profile(
        self, async_session: AsyncSession, clean_tables,
    ):
        """Las fases enviadas se aplican aunque pertenezcan a otro perfil."""
        from app.schemas.event_day_phase import EventDayPhaseCreate

        e, al, pa, _pb, _pha, phb = await self._setup(async_session)
        day = await self._make_day(async_session, e, al, pa, [])

        updated = await update_event_day(
            async_session,
            day,
            EventDayUpdate(
                phases=[
                    EventDayPhaseCreate(
                        operational_phase_id=phb, start_min=0, end_min=300, intensity=1.0,
                    )
                ],
            ),
        )
        assert updated.operational_profile_id == pa
        phases = await list_phases_by_event_day(async_session, day.id)
        assert [p.operational_phase_id for p in phases] == [phb]

    async def test_create_phase_from_other_profile_accepted(
        self, async_session: AsyncSession, clean_tables,
    ):
        """Agregar una EventDayPhase de otro perfil es válido bajo RFC-007."""
        from app.schemas.event_day_phase import EventDayPhaseCreate

        e, al, pa, _pb, pha, phb = await self._setup(async_session)
        day = await self._make_day(async_session, e, al, pa, [pha])

        added = await create_event_day_phase(
            async_session, day.id,
            EventDayPhaseCreate(
                operational_phase_id=phb, start_min=300, end_min=400, intensity=1.0,
            ),
        )
        assert added.operational_phase_id == phb

    async def test_update_phase_to_other_profile_accepted(
        self, async_session: AsyncSession, clean_tables,
    ):
        """Reasignar una EventDayPhase a una fase de otro perfil es válido."""
        from app.schemas.event_day_phase import EventDayPhaseCreate

        e, al, pa, _pb, pha, phb = await self._setup(async_session)
        day = await self._make_day(async_session, e, al, pa, [pha])
        phase = await create_event_day_phase(
            async_session, day.id,
            EventDayPhaseCreate(
                operational_phase_id=pha, start_min=0, end_min=300, intensity=1.0,
            ),
        )

        updated = await update_event_day_phase(
            async_session, phase, EventDayPhaseUpdate(operational_phase_id=phb),
        )
        assert updated.operational_phase_id == phb

    async def test_valid_profile_change_replaces_all_phases(
        self, async_session: AsyncSession, clean_tables,
    ):
        """Caso válido: cambiar perfil + fases completas del nuevo perfil → OK."""
        from app.schemas.event_day_phase import EventDayPhaseCreate

        e, al, pa, pb, pha, phb = await self._setup(async_session)
        day = await self._make_day(async_session, e, al, pa, [pha])

        updated = await update_event_day(
            async_session, day,
            EventDayUpdate(
                operational_profile_id=pb,
                phases=[
                    EventDayPhaseCreate(
                        operational_phase_id=phb, start_min=0, end_min=300, intensity=1.0,
                    )
                ],
            ),
        )
        assert updated.operational_profile_id == pb
        phases = await list_phases_by_event_day(async_session, day.id)
        assert len(phases) == 1
        assert phases[0].operational_phase_id == phb

    async def test_valid_add_phase_same_profile(
        self, async_session: AsyncSession, clean_tables,
    ):
        """Caso válido: agregar una fase del perfil del día → OK."""
        from app.schemas.event_day_phase import EventDayPhaseCreate

        e, al, pa, _pb, pha, _phb = await self._setup(async_session)
        day = await self._make_day(async_session, e, al, pa, [pha])

        added = await create_event_day_phase(
            async_session, day.id,
            EventDayPhaseCreate(
                operational_phase_id=pha, start_min=0, end_min=300, intensity=1.0,
            ),
        )
        assert added.operational_phase_id == pha
