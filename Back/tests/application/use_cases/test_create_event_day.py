from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.application.context_engine.exceptions import InvalidConfiguration
from src.application.use_cases.create_event_day import CreateEventDay
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.operational_profile import OperationalProfile


@pytest.fixture
def phase_a() -> OperationalPhase:
    return OperationalPhase(
        id=UUID("10000000-0000-0000-0000-000000000001"),
        name="Opening",
        sequence_order=1,
    )


@pytest.fixture
def phase_b() -> OperationalPhase:
    return OperationalPhase(
        id=UUID("20000000-0000-0000-0000-000000000002"),
        name="Peak",
        sequence_order=2,
    )


@pytest.fixture
def profile(phase_a: OperationalPhase, phase_b: OperationalPhase) -> OperationalProfile:
    return OperationalProfile(
        id=UUID("30000000-0000-0000-0000-000000000003"),
        name="Test Profile",
        phases=(phase_a, phase_b),
    )


@pytest.fixture
def event_day_phase_a(phase_a: OperationalPhase) -> EventDayPhase:
    return EventDayPhase(
        id=UUID("40000000-0000-0000-0000-000000000004"),
        event_day_id=UUID("60000000-0000-0000-0000-000000000006"),
        operational_phase_id=phase_a.id,
        start_min=1200,
        end_min=1380,
    )


@pytest.fixture
def event_day_phase_b(phase_b: OperationalPhase) -> EventDayPhase:
    return EventDayPhase(
        id=UUID("50000000-0000-0000-0000-000000000005"),
        event_day_id=UUID("60000000-0000-0000-0000-000000000006"),
        operational_phase_id=phase_b.id,
        start_min=1380,
        end_min=1680,
    )


@pytest.fixture
def valid_phases(
    event_day_phase_a: EventDayPhase,
    event_day_phase_b: EventDayPhase,
) -> tuple[EventDayPhase, ...]:
    return (event_day_phase_a, event_day_phase_b)


@pytest.fixture
def event_date() -> date:
    return date(2026, 1, 10)


@pytest.fixture
def saved_event_day(
    event_date: date,
    profile: OperationalProfile,
    event_day_phase_a: EventDayPhase,
    event_day_phase_b: EventDayPhase,
) -> EventDay:
    phases = (event_day_phase_a, event_day_phase_b)
    return EventDay(
        id=UUID("60000000-0000-0000-0000-000000000006"),
        event_date=event_date,
        operational_profile_id=profile.id,
        attendance_level_id=UUID("70000000-0000-0000-0000-000000000007"),
        operational_start_min=1200,
        operational_end_min=1680,
        phases=phases,
    )


@pytest.fixture
def event_day_repo(saved_event_day: EventDay) -> AsyncMock:
    repo = AsyncMock()
    repo.save = AsyncMock(return_value=saved_event_day)
    return repo


@pytest.fixture
def operational_profile_repo(profile: OperationalProfile) -> AsyncMock:
    repo = AsyncMock()
    repo.find_by_id = AsyncMock(return_value=profile)
    return repo


@pytest.fixture
def use_case(
    event_day_repo: AsyncMock,
    operational_profile_repo: AsyncMock,
) -> CreateEventDay:
    return CreateEventDay(
        event_day_repo=event_day_repo,
        operational_profile_repo=operational_profile_repo,
    )


class TestCreateEventDay:
    async def test_creates_and_persists_event_day(
        self,
        use_case: CreateEventDay,
        event_day_repo: AsyncMock,
        event_date: date,
        profile: OperationalProfile,
        valid_phases: tuple[EventDayPhase, ...],
    ) -> None:
        result = await use_case.execute(
            event_date=event_date,
            operational_profile_id=profile.id,
            attendance_level_id=UUID("70000000-0000-0000-0000-000000000007"),
            operational_start_min=1200,
            operational_end_min=1680,
            phases=valid_phases,
        )

        assert isinstance(result, EventDay)

    async def test_saves_exactly_once(
        self,
        use_case: CreateEventDay,
        event_day_repo: AsyncMock,
        event_date: date,
        profile: OperationalProfile,
        valid_phases: tuple[EventDayPhase, ...],
    ) -> None:
        await use_case.execute(
            event_date=event_date,
            operational_profile_id=profile.id,
            attendance_level_id=UUID("70000000-0000-0000-0000-000000000007"),
            operational_start_min=1200,
            operational_end_min=1680,
            phases=valid_phases,
        )

        event_day_repo.save.assert_awaited_once()

    async def test_returns_saved_event_day(
        self,
        use_case: CreateEventDay,
        event_day_repo: AsyncMock,
        event_date: date,
        profile: OperationalProfile,
        valid_phases: tuple[EventDayPhase, ...],
        saved_event_day: EventDay,
    ) -> None:
        event_day_repo.save = AsyncMock(return_value=saved_event_day)

        result = await use_case.execute(
            event_date=event_date,
            operational_profile_id=profile.id,
            attendance_level_id=UUID("70000000-0000-0000-0000-000000000007"),
            operational_start_min=1200,
            operational_end_min=1680,
            phases=valid_phases,
        )

        assert result is saved_event_day

    async def test_rejects_overlapping_phases(
        self,
        use_case: CreateEventDay,
        event_date: date,
        profile: OperationalProfile,
        event_day_phase_a: EventDayPhase,
        event_day_phase_b: EventDayPhase,
    ) -> None:
        overlapping_phase = EventDayPhase(
            id=UUID("80000000-0000-0000-0000-000000000008"),
            event_day_id=UUID("60000000-0000-0000-0000-000000000006"),
            operational_phase_id=event_day_phase_b.operational_phase_id,
            start_min=1300,
            end_min=1600,
        )
        phases = (event_day_phase_a, overlapping_phase)

        with pytest.raises(InvalidConfiguration):
            await use_case.execute(
                event_date=event_date,
                operational_profile_id=profile.id,
                attendance_level_id=UUID("70000000-0000-0000-0000-000000000007"),
                operational_start_min=1200,
                operational_end_min=1680,
                phases=phases,
            )

    async def test_rejects_coverage_gap(
        self,
        use_case: CreateEventDay,
        event_date: date,
        profile: OperationalProfile,
        event_day_phase_a: EventDayPhase,
        event_day_phase_b: EventDayPhase,
    ) -> None:
        gap_phase = EventDayPhase(
            id=UUID("90000000-0000-0000-0000-000000000009"),
            event_day_id=UUID("60000000-0000-0000-0000-000000000006"),
            operational_phase_id=event_day_phase_b.operational_phase_id,
            start_min=1400,
            end_min=1680,
        )
        phases = (event_day_phase_a, gap_phase)

        with pytest.raises(InvalidConfiguration):
            await use_case.execute(
                event_date=event_date,
                operational_profile_id=profile.id,
                attendance_level_id=UUID("70000000-0000-0000-0000-000000000007"),
                operational_start_min=1200,
                operational_end_min=1680,
                phases=phases,
            )

    async def test_rejects_wrong_phase_order(
        self,
        use_case: CreateEventDay,
        event_date: date,
        profile: OperationalProfile,
        phase_a: OperationalPhase,
        phase_b: OperationalPhase,
    ) -> None:
        first = EventDayPhase(
            id=UUID("40000000-0000-0000-0000-000000000004"),
            event_day_id=UUID("60000000-0000-0000-0000-000000000006"),
            operational_phase_id=phase_b.id,
            start_min=1200,
            end_min=1380,
        )
        second = EventDayPhase(
            id=UUID("50000000-0000-0000-0000-000000000005"),
            event_day_id=UUID("60000000-0000-0000-0000-000000000006"),
            operational_phase_id=phase_a.id,
            start_min=1380,
            end_min=1680,
        )
        swapped_phases = (first, second)

        with pytest.raises(InvalidConfiguration):
            await use_case.execute(
                event_date=event_date,
                operational_profile_id=profile.id,
                attendance_level_id=UUID("70000000-0000-0000-0000-000000000007"),
                operational_start_min=1200,
                operational_end_min=1680,
                phases=swapped_phases,
            )

    async def test_rejects_missing_operational_profile(
        self,
        use_case: CreateEventDay,
        operational_profile_repo: AsyncMock,
        event_date: date,
        valid_phases: tuple[EventDayPhase, ...],
    ) -> None:
        operational_profile_repo.find_by_id = AsyncMock(return_value=None)

        with pytest.raises(InvalidConfiguration):
            await use_case.execute(
                event_date=event_date,
                operational_profile_id=UUID("00000000-0000-0000-0000-000000000000"),
                attendance_level_id=UUID("70000000-0000-0000-0000-000000000007"),
                operational_start_min=1200,
                operational_end_min=1680,
                phases=valid_phases,
            )

    async def test_does_not_save_when_validation_fails(
        self,
        use_case: CreateEventDay,
        event_day_repo: AsyncMock,
        event_date: date,
        profile: OperationalProfile,
        phase_a: OperationalPhase,
        phase_b: OperationalPhase,
    ) -> None:
        first = EventDayPhase(
            id=UUID("40000000-0000-0000-0000-000000000004"),
            event_day_id=UUID("60000000-0000-0000-0000-000000000006"),
            operational_phase_id=phase_b.id,
            start_min=1200,
            end_min=1380,
        )
        second = EventDayPhase(
            id=UUID("50000000-0000-0000-0000-000000000005"),
            event_day_id=UUID("60000000-0000-0000-0000-000000000006"),
            operational_phase_id=phase_a.id,
            start_min=1380,
            end_min=1680,
        )
        swapped_phases = (first, second)

        with pytest.raises(InvalidConfiguration):
            await use_case.execute(
                event_date=event_date,
                operational_profile_id=profile.id,
                attendance_level_id=UUID("70000000-0000-0000-0000-000000000007"),
                operational_start_min=1200,
                operational_end_min=1680,
                phases=swapped_phases,
            )

        event_day_repo.save.assert_not_called()

    async def test_propagates_save_error(
        self,
        use_case: CreateEventDay,
        event_day_repo: AsyncMock,
        event_date: date,
        profile: OperationalProfile,
        valid_phases: tuple[EventDayPhase, ...],
    ) -> None:
        event_day_repo.save = AsyncMock(side_effect=RuntimeError("DB failure"))

        with pytest.raises(RuntimeError):
            await use_case.execute(
                event_date=event_date,
                operational_profile_id=profile.id,
                attendance_level_id=UUID("70000000-0000-0000-0000-000000000007"),
                operational_start_min=1200,
                operational_end_min=1680,
                phases=valid_phases,
            )

    async def test_does_not_access_context_engine(
        self,
        use_case: CreateEventDay,
        event_date: date,
        profile: OperationalProfile,
        valid_phases: tuple[EventDayPhase, ...],
    ) -> None:
        result = await use_case.execute(
            event_date=event_date,
            operational_profile_id=profile.id,
            attendance_level_id=UUID("70000000-0000-0000-0000-000000000007"),
            operational_start_min=1200,
            operational_end_min=1680,
            phases=valid_phases,
        )

        assert isinstance(result, EventDay)
