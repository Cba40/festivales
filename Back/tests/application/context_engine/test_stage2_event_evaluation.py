from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

import pytest

from src.application.context_engine.stage2_event_evaluation import (
    apply_dynamic_events,
)
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_event import OperationalEvent
from src.domain.entities.operational_phase import OperationalPhase


@pytest.fixture
def active_phase() -> OperationalPhase:
    return OperationalPhase(
        id=UUID("10000000-0000-0000-0000-000000000001"),
        name="Peak",
        sequence_order=2,
    )


@pytest.fixture
def active_day_phase() -> EventDayPhase:
    return EventDayPhase(
        event_day_id=UUID("30000000-0000-0000-0000-000000000001"),
        operational_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
        start_min=840,
        end_min=1080,
        id=UUID("40000000-0000-0000-0000-000000000002"),
    )


@pytest.fixture
def zone_a() -> UUID:
    return UUID("a0000000-0000-0000-0000-000000000001")


@pytest.fixture
def zone_b() -> UUID:
    return UUID("b0000000-0000-0000-0000-000000000001")


@pytest.fixture
def timestamp() -> datetime:
    return datetime(2026, 7, 15, 15, 0)


class TestNoActiveEvents:
    def test_returns_empty_impacts_when_no_events(
        self,
        active_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
    ) -> None:
        context = apply_dynamic_events(
            active_phase, active_day_phase, [], timestamp
        )
        assert context.event_impacts == {}
        assert context.active_operational_phase is active_phase
        assert context.active_event_day_phase is active_day_phase
        assert context.timestamp == timestamp

    def test_returns_empty_impacts_when_all_events_outside_window(
        self,
        active_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: UUID,
    ) -> None:
        event = OperationalEvent(
            target_zone_id=zone_a,
            impact_value=50,
            is_incident=False,
            start_timestamp=datetime(2026, 7, 15, 16, 0),
            end_timestamp=datetime(2026, 7, 15, 18, 0),
            id=UUID("50000000-0000-0000-0000-000000000001"),
        )
        context = apply_dynamic_events(
            active_phase, active_day_phase, [event], timestamp
        )
        assert context.event_impacts == {}


class TestSingleActiveEvent:
    def test_applies_positive_impact(
        self,
        active_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: UUID,
    ) -> None:
        event = OperationalEvent(
            target_zone_id=zone_a,
            impact_value=30,
            is_incident=False,
            start_timestamp=datetime(2026, 7, 15, 14, 0),
            end_timestamp=datetime(2026, 7, 15, 16, 0),
            id=UUID("50000000-0000-0000-0000-000000000001"),
        )
        context = apply_dynamic_events(
            active_phase, active_day_phase, [event], timestamp
        )
        assert context.event_impacts == {zone_a: 30}

    def test_applies_negative_impact(
        self,
        active_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: UUID,
    ) -> None:
        event = OperationalEvent(
            target_zone_id=zone_a,
            impact_value=-40,
            is_incident=False,
            start_timestamp=datetime(2026, 7, 15, 14, 0),
            end_timestamp=datetime(2026, 7, 15, 16, 0),
            id=UUID("50000000-0000-0000-0000-000000000001"),
        )
        context = apply_dynamic_events(
            active_phase, active_day_phase, [event], timestamp
        )
        assert context.event_impacts == {zone_a: -40}


class TestMultipleEvents:
    def test_sums_impacts_same_zone(
        self,
        active_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: UUID,
    ) -> None:
        event_1 = OperationalEvent(
            target_zone_id=zone_a,
            impact_value=20,
            is_incident=False,
            start_timestamp=datetime(2026, 7, 15, 14, 0),
            end_timestamp=datetime(2026, 7, 15, 16, 0),
            id=UUID("50000000-0000-0000-0000-000000000001"),
        )
        event_2 = OperationalEvent(
            target_zone_id=zone_a,
            impact_value=-10,
            is_incident=False,
            start_timestamp=datetime(2026, 7, 15, 14, 30),
            end_timestamp=datetime(2026, 7, 15, 17, 0),
            id=UUID("50000000-0000-0000-0000-000000000002"),
        )
        context = apply_dynamic_events(
            active_phase, active_day_phase, [event_1, event_2], timestamp
        )
        assert context.event_impacts == {zone_a: 10}

    def test_accumulates_impacts_multiple_zones(
        self,
        active_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: UUID,
        zone_b: UUID,
    ) -> None:
        event_a = OperationalEvent(
            target_zone_id=zone_a,
            impact_value=25,
            is_incident=False,
            start_timestamp=datetime(2026, 7, 15, 14, 0),
            end_timestamp=datetime(2026, 7, 15, 16, 0),
            id=UUID("50000000-0000-0000-0000-000000000001"),
        )
        event_b = OperationalEvent(
            target_zone_id=zone_b,
            impact_value=-15,
            is_incident=False,
            start_timestamp=datetime(2026, 7, 15, 14, 0),
            end_timestamp=datetime(2026, 7, 15, 16, 0),
            id=UUID("50000000-0000-0000-0000-000000000002"),
        )
        context = apply_dynamic_events(
            active_phase, active_day_phase, [event_a, event_b], timestamp
        )
        assert context.event_impacts == {zone_a: 25, zone_b: -15}

    def test_mixed_active_and_inactive_events(
        self,
        active_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: UUID,
    ) -> None:
        active_event = OperationalEvent(
            target_zone_id=zone_a,
            impact_value=50,
            is_incident=False,
            start_timestamp=datetime(2026, 7, 15, 14, 0),
            end_timestamp=datetime(2026, 7, 15, 16, 0),
            id=UUID("50000000-0000-0000-0000-000000000001"),
        )
        inactive_event = OperationalEvent(
            target_zone_id=zone_a,
            impact_value=100,
            is_incident=False,
            start_timestamp=datetime(2026, 7, 15, 10, 0),
            end_timestamp=datetime(2026, 7, 15, 12, 0),
            id=UUID("50000000-0000-0000-0000-000000000002"),
        )
        context = apply_dynamic_events(
            active_phase, active_day_phase, [active_event, inactive_event], timestamp
        )
        assert context.event_impacts == {zone_a: 50}


class TestBoundaryConditions:
    def test_start_timestamp_inclusive(
        self,
        active_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        zone_a: UUID,
    ) -> None:
        ts = datetime(2026, 7, 15, 14, 0)
        event = OperationalEvent(
            target_zone_id=zone_a,
            impact_value=30,
            is_incident=False,
            start_timestamp=datetime(2026, 7, 15, 14, 0),
            end_timestamp=datetime(2026, 7, 15, 16, 0),
            id=UUID("50000000-0000-0000-0000-000000000001"),
        )
        context = apply_dynamic_events(
            active_phase, active_day_phase, [event], ts
        )
        assert context.event_impacts == {zone_a: 30}

    def test_end_timestamp_exclusive(
        self,
        active_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        zone_a: UUID,
    ) -> None:
        ts = datetime(2026, 7, 15, 16, 0)
        event = OperationalEvent(
            target_zone_id=zone_a,
            impact_value=30,
            is_incident=False,
            start_timestamp=datetime(2026, 7, 15, 14, 0),
            end_timestamp=datetime(2026, 7, 15, 16, 0),
            id=UUID("50000000-0000-0000-0000-000000000001"),
        )
        context = apply_dynamic_events(
            active_phase, active_day_phase, [event], ts
        )
        assert context.event_impacts == {}


class TestImpactClamping:
    def test_clamps_sum_below_negative_100(
        self,
        active_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: UUID,
    ) -> None:
        event_1 = OperationalEvent(
            target_zone_id=zone_a,
            impact_value=-60,
            is_incident=False,
            start_timestamp=datetime(2026, 7, 15, 14, 0),
            end_timestamp=datetime(2026, 7, 15, 16, 0),
            id=UUID("50000000-0000-0000-0000-000000000001"),
        )
        event_2 = OperationalEvent(
            target_zone_id=zone_a,
            impact_value=-50,
            is_incident=False,
            start_timestamp=datetime(2026, 7, 15, 14, 30),
            end_timestamp=datetime(2026, 7, 15, 17, 0),
            id=UUID("50000000-0000-0000-0000-000000000002"),
        )
        context = apply_dynamic_events(
            active_phase, active_day_phase, [event_1, event_2], timestamp
        )
        assert context.event_impacts == {zone_a: -100}

    def test_exact_negative_100_not_clamped(
        self,
        active_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: UUID,
    ) -> None:
        event = OperationalEvent(
            target_zone_id=zone_a,
            impact_value=-100,
            is_incident=True,
            start_timestamp=datetime(2026, 7, 15, 14, 0),
            end_timestamp=datetime(2026, 7, 15, 16, 0),
            id=UUID("50000000-0000-0000-0000-000000000001"),
        )
        context = apply_dynamic_events(
            active_phase, active_day_phase, [event], timestamp
        )
        assert context.event_impacts == {zone_a: -100}
