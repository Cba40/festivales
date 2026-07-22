"""Tests unitarios de CRUD P3.0 — integridad referencial, unicidad, validaciones.

Cubre §13: unicidad de nombre, clave compuesta, FK validation, filtro de eventos activos.
"""
import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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
from app.db.session import Base
from app.schemas.event_day import EventDayCreate
from app.schemas.event_day_phase import EventDayPhaseUpdate
from app.schemas.operational_event import OperationalEventCreate
from app.schemas.operational_event_modifier import OperationalEventModifierCreate
from app.schemas.operational_phase import OperationalPhaseCreate
from app.schemas.operational_profile import OperationalProfileCreate
from app.schemas.zone_behavior import ZoneBehaviorCreate

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
                start_min=0,
                end_min=600,
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
                start_min=0,
                end_min=300,
                sort_order=1,
            ),
        )
        with pytest.raises(ValueError) as exc_info:
            await create_operational_phase(
                async_session,
                OperationalPhaseCreate(
                    operational_profile_id=profile_id,
                    name="Fase2",
                    start_min=300,
                    end_min=600,
                    sort_order=1,
                ),
            )
        assert "sort_order" in str(exc_info.value).lower() or "already exists" in str(exc_info.value)


@pytest.mark.asyncio
class TestZoneBehaviorCRUD:

    async def test_zone_behavior_composite_key_uniqueness(
        self, async_session: AsyncSession, seed_profile_and_phase, seed_zone_types, clean_tables,
    ):
        """§13: Crear dos ZoneBehavior con misma (phase_id, zone_type_id) → ValueError."""
        profile_id, phase_id = seed_profile_and_phase
        zt_id = "zt-estacionamiento"

        await create_zone_behavior(
            async_session,
            ZoneBehaviorCreate(
                operational_phase_id=phase_id,
                zone_type_id=zt_id,
                saturation_factor=1.0,
                availability_factor=1.0,
                resource_factor=1.0,
                priority_weight=1.0,
            ),
        )
        with pytest.raises(ValueError) as exc_info:
            await create_zone_behavior(
                async_session,
                ZoneBehaviorCreate(
                    operational_phase_id=phase_id,
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
                start_min=0,
                end_min=600,
                sort_order=1,
            ),
        )
        p2 = await create_operational_phase(
            async_session,
            OperationalPhaseCreate(
                operational_profile_id=prof.id,
                name="EDP Fase2",
                start_min=600,
                end_min=1200,
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
