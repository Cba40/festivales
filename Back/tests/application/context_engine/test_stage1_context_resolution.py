from collections.abc import Mapping
from datetime import date, datetime
from uuid import UUID

import pytest

from src.application.context_engine.exceptions import InvalidPhaseContext
from src.application.context_engine.stage1_context_resolution import (
    resolve_contextual_phase,
)
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase


@pytest.fixture
def opening_phase() -> OperationalPhase:
    return OperationalPhase(
        id=UUID("10000000-0000-0000-0000-000000000001"),
        name="Opening",
        sequence_order=1,
    )


@pytest.fixture
def peak_phase() -> OperationalPhase:
    return OperationalPhase(
        id=UUID("10000000-0000-0000-0000-000000000002"),
        name="Peak",
        sequence_order=2,
    )


@pytest.fixture
def closing_phase() -> OperationalPhase:
    return OperationalPhase(
        id=UUID("10000000-0000-0000-0000-000000000003"),
        name="Closing",
        sequence_order=3,
    )


@pytest.fixture
def operational_phases(
    opening_phase: OperationalPhase,
    peak_phase: OperationalPhase,
    closing_phase: OperationalPhase,
) -> Mapping[UUID, OperationalPhase]:
    return {
        opening_phase.id: opening_phase,
        peak_phase.id: peak_phase,
        closing_phase.id: closing_phase,
    }


@pytest.fixture
def event_day_id() -> UUID:
    return UUID("30000000-0000-0000-0000-000000000001")


@pytest.fixture
def normal_phases(
    event_day_id: UUID,
    opening_phase: OperationalPhase,
    peak_phase: OperationalPhase,
    closing_phase: OperationalPhase,
) -> tuple[EventDayPhase, EventDayPhase, EventDayPhase]:
    ed_phase_1 = EventDayPhase(
        event_day_id=event_day_id,
        operational_phase_id=opening_phase.id,
        start_min=600,
        end_min=840,
        id=UUID("40000000-0000-0000-0000-000000000001"),
    )
    ed_phase_2 = EventDayPhase(
        event_day_id=event_day_id,
        operational_phase_id=peak_phase.id,
        start_min=840,
        end_min=1080,
        id=UUID("40000000-0000-0000-0000-000000000002"),
    )
    ed_phase_3 = EventDayPhase(
        event_day_id=event_day_id,
        operational_phase_id=closing_phase.id,
        start_min=1080,
        end_min=1320,
        id=UUID("40000000-0000-0000-0000-000000000003"),
    )
    return ed_phase_1, ed_phase_2, ed_phase_3


@pytest.fixture
def normal_event_day(
    event_day_id: UUID,
    normal_phases: tuple[EventDayPhase, EventDayPhase, EventDayPhase],
) -> EventDay:
    return EventDay(
        id=event_day_id,
        event_date=date(2026, 7, 15),
        operational_profile_id=UUID("20000000-0000-0000-0000-000000000001"),
        attendance_level_id=UUID("00000000-0000-0000-0000-000000000001"),
        operational_start_min=600,
        operational_end_min=1320,
        phases=normal_phases,
    )


class TestResolutionNormalCases:
    def test_resolves_first_phase(
        self,
        normal_event_day: EventDay,
        operational_phases: Mapping[UUID, OperationalPhase],
        normal_phases: tuple[EventDayPhase, EventDayPhase, EventDayPhase],
        opening_phase: OperationalPhase,
    ) -> None:
        timestamp = datetime(2026, 7, 15, 10, 30)
        ed_phase, op_phase = resolve_contextual_phase(
            normal_event_day, operational_phases, timestamp
        )
        assert ed_phase is normal_phases[0]
        assert ed_phase.start_min == 600
        assert ed_phase.end_min == 840
        assert op_phase is opening_phase

    def test_resolves_middle_phase(
        self,
        normal_event_day: EventDay,
        operational_phases: Mapping[UUID, OperationalPhase],
        normal_phases: tuple[EventDayPhase, EventDayPhase, EventDayPhase],
        peak_phase: OperationalPhase,
    ) -> None:
        timestamp = datetime(2026, 7, 15, 15, 0)
        ed_phase, op_phase = resolve_contextual_phase(
            normal_event_day, operational_phases, timestamp
        )
        assert ed_phase is normal_phases[1]
        assert ed_phase.start_min == 840
        assert ed_phase.end_min == 1080
        assert op_phase is peak_phase

    def test_resolves_last_phase(
        self,
        normal_event_day: EventDay,
        operational_phases: Mapping[UUID, OperationalPhase],
        normal_phases: tuple[EventDayPhase, EventDayPhase, EventDayPhase],
        closing_phase: OperationalPhase,
    ) -> None:
        timestamp = datetime(2026, 7, 15, 21, 0)
        ed_phase, op_phase = resolve_contextual_phase(
            normal_event_day, operational_phases, timestamp
        )
        assert ed_phase is normal_phases[2]
        assert ed_phase.start_min == 1080
        assert ed_phase.end_min == 1320
        assert op_phase is closing_phase


@pytest.fixture
def midnight_phases(
    event_day_id: UUID,
    peak_phase: OperationalPhase,
) -> tuple[EventDayPhase, ...]:
    ed_phase = EventDayPhase(
        event_day_id=event_day_id,
        operational_phase_id=peak_phase.id,
        start_min=1200,
        end_min=1680,
        id=UUID("40000000-0000-0000-0000-000000000004"),
    )
    return (ed_phase,)


@pytest.fixture
def midnight_event_day(
    event_day_id: UUID,
    midnight_phases: tuple[EventDayPhase, ...],
) -> EventDay:
    return EventDay(
        id=event_day_id,
        event_date=date(2026, 7, 15),
        operational_profile_id=UUID("20000000-0000-0000-0000-000000000001"),
        attendance_level_id=UUID("00000000-0000-0000-0000-000000000001"),
        operational_start_min=1200,
        operational_end_min=1680,
        phases=midnight_phases,
    )


class TestMidnightCrossing:
    def test_resolves_phase_after_midnight(
        self,
        midnight_event_day: EventDay,
        operational_phases: Mapping[UUID, OperationalPhase],
        midnight_phases: tuple[EventDayPhase, ...],
        peak_phase: OperationalPhase,
    ) -> None:
        timestamp = datetime(2026, 7, 16, 2, 30)
        ed_phase, op_phase = resolve_contextual_phase(
            midnight_event_day, operational_phases, timestamp
        )
        assert ed_phase is midnight_phases[0]
        assert ed_phase.start_min == 1200
        assert ed_phase.end_min == 1680
        assert op_phase is peak_phase

    def test_resolves_phase_before_midnight_same_phase(
        self,
        midnight_event_day: EventDay,
        operational_phases: Mapping[UUID, OperationalPhase],
        midnight_phases: tuple[EventDayPhase, ...],
        peak_phase: OperationalPhase,
    ) -> None:
        timestamp = datetime(2026, 7, 15, 22, 0)
        ed_phase, op_phase = resolve_contextual_phase(
            midnight_event_day, operational_phases, timestamp
        )
        assert ed_phase is midnight_phases[0]
        assert ed_phase.start_min == 1200
        assert ed_phase.end_min == 1680
        assert op_phase is peak_phase


class TestBoundaryConditions:
    def test_exact_start_min_boundary(
        self,
        normal_event_day: EventDay,
        operational_phases: Mapping[UUID, OperationalPhase],
        normal_phases: tuple[EventDayPhase, EventDayPhase, EventDayPhase],
        opening_phase: OperationalPhase,
    ) -> None:
        timestamp = datetime(2026, 7, 15, 10, 0)
        ed_phase, op_phase = resolve_contextual_phase(
            normal_event_day, operational_phases, timestamp
        )
        assert ed_phase is normal_phases[0]
        assert op_phase is opening_phase

    def test_end_min_exclusive(
        self,
        normal_event_day: EventDay,
        operational_phases: Mapping[UUID, OperationalPhase],
        normal_phases: tuple[EventDayPhase, EventDayPhase, EventDayPhase],
        peak_phase: OperationalPhase,
    ) -> None:
        timestamp = datetime(2026, 7, 15, 14, 0)
        ed_phase, op_phase = resolve_contextual_phase(
            normal_event_day, operational_phases, timestamp
        )
        assert ed_phase is normal_phases[1]
        assert op_phase is peak_phase


class TestInvalidPhaseContext:
    def test_timestamp_outside_all_phases(
        self,
        normal_event_day: EventDay,
        operational_phases: Mapping[UUID, OperationalPhase],
    ) -> None:
        timestamp = datetime(2026, 7, 15, 23, 0)
        with pytest.raises(InvalidPhaseContext, match="INVALID_PHASE_CONTEXT"):
            resolve_contextual_phase(
                normal_event_day, operational_phases, timestamp
            )

    def test_timestamp_before_operational_window(
        self,
        normal_event_day: EventDay,
        operational_phases: Mapping[UUID, OperationalPhase],
    ) -> None:
        timestamp = datetime(2026, 7, 15, 8, 0)
        with pytest.raises(InvalidPhaseContext, match="INVALID_PHASE_CONTEXT"):
            resolve_contextual_phase(
                normal_event_day, operational_phases, timestamp
            )
