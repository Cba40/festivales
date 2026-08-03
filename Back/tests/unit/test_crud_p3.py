"""Tests unitarios de CRUD P3.0 — integridad referencial, unicidad, validaciones.

Cubre §13: unicidad de nombre, clave compuesta, FK validation, filtro de eventos activos.
"""
import os
import uuid

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.crud import (
    create_event_day,
    create_event_day_phase,
    create_operational_event,
    create_operational_event_modifier,
    create_operational_phase,
    create_operational_profile,
    create_zone_behavior,
    get_operational_event,
    list_active_by_event_day,
    list_events_by_event_day,
    list_phases_by_profile,
    update_event_day_phase,
    update_operational_profile,
    update_operational_phase,
)
from app.crud.zone_type import zone_type as zone_type_crud
from app.db.session import Base
from app.schemas.event_day import EventDayCreate
from app.schemas.event_day_phase import EventDayPhaseUpdate
from app.schemas.operational_event import OperationalEventCreate
from app.schemas.operational_event_modifier import OperationalEventModifierCreate
from app.schemas.operational_phase import OperationalPhaseCreate
from app.schemas.operational_profile import OperationalProfileCreate
from app.schemas.zone_behavior import ZoneBehaviorCreate
from app.schemas.zone_type import ZoneTypeCreate

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", settings.DATABASE_URL)


# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def async_engine():
    async_url = TEST_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(async_url)
    return engine


@pytest.fixture
async def async_session(async_engine):
    async with async_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn)
        yield session
        await conn.rollback()


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
class TestOperationalEventModifierCRUD:

    async def test_operational_event_modifier_uniqueness(
        self, async_session: AsyncSession, seed_zone_types, clean_tables,
    ):
        """§13: Crear dos modificadores con mismo (event_type, zone_type_id) → ValueError."""
        zt_id = "zt-estacionamiento"

        await create_operational_event_modifier(
            async_session,
            OperationalEventModifierCreate(
                event_type="tormenta",
                zone_type_id=zt_id,
                saturation_multiplier=1.5,
                availability_multiplier=0.8,
                priority_modifier=0.3,
            ),
        )

        with pytest.raises(ValueError) as exc_info:
            await create_operational_event_modifier(
                async_session,
                OperationalEventModifierCreate(
                    event_type="tormenta",
                    zone_type_id=zt_id,
                    saturation_multiplier=2.0,
                    availability_multiplier=1.0,
                    priority_modifier=0.0,
                ),
            )
        assert "already exists" in str(exc_info.value)


@pytest.mark.asyncio
class TestOperationalEventCRUD:

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
                             min_people=0, max_people=100000, global_multiplier=1.0)
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
            estimated_attendance=10000,
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

    async def test_event_day_create_validates_profile_exists(
        self, async_session: AsyncSession, clean_tables,
    ):
        """§13: Crear EventDay con operational_profile_id inexistente → ValueError."""
        from app.models.attendance_level import AttendanceLevel
        from app.models.event import Event

        event = Event(id="test-event-crud-al", name="AL Test", description="")
        async_session.add(event)
        al = AttendanceLevel(id="al-crud-test", event_id=event.id, name="TestAL",
                             min_people=0, max_people=100000, global_multiplier=1.0)
        async_session.add(al)
        await async_session.flush()

        fake_profile_id = uuid.uuid4()
        with pytest.raises(ValueError) as exc_info:
            await create_event_day(
                async_session,
                EventDayCreate(
                    date="2026-07-10",
                    day_of_week="jueves",
                    operational_profile_id=fake_profile_id,
                    operational_start_min=480,
                    operational_end_min=1800,
                    estimated_attendance=1000,
                    attendance_level_id=al.id,
                ),
                event_id="test-event-crud-al",
            )
        assert "not found" in str(exc_info.value).lower()


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
                             min_people=0, max_people=100000, global_multiplier=1.0)
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
            estimated_attendance=10000,
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


@pytest.mark.asyncio
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
        self, async_session: AsyncSession, clean_tables,
    ):
        """Si la creación automática falla → rollback completo, sin datos parciales."""
        from unittest.mock import patch

        from app.models.operational_phase import OperationalPhase

        profile = await create_operational_profile(
            async_session, OperationalProfileCreate(name="P31A-Rollback", description=""),
        )

        with patch(
            "app.crud.operational_phase.default_behavior",
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
