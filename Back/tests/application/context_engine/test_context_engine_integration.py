from datetime import date, datetime
from uuid import UUID

import pytest

from src.application.context_engine.context_engine import ContextEngine
from src.application.context_engine.exceptions import (
    BehaviorNotDefined,
    InvalidPhaseContext,
)
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_event import OperationalEvent
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction, ZoneBehavior
from src.domain.value_objects.territorial_prediction import TerritorialPrediction


@pytest.fixture
def engine() -> ContextEngine:
    return ContextEngine()


@pytest.fixture
def timestamp() -> datetime:
    return datetime(2026, 7, 15, 15, 0)


@pytest.fixture
def peak_phase() -> OperationalPhase:
    return OperationalPhase(
        id=UUID("10000000-0000-0000-0000-000000000001"),
        name="Peak",
        sequence_order=2,
    )


@pytest.fixture
def opening_phase() -> OperationalPhase:
    return OperationalPhase(
        id=UUID("10000000-0000-0000-0000-000000000002"),
        name="Opening",
        sequence_order=1,
    )


@pytest.fixture
def operational_phases(
    peak_phase: OperationalPhase,
    opening_phase: OperationalPhase,
) -> dict[UUID, OperationalPhase]:
    return {peak_phase.id: peak_phase, opening_phase.id: opening_phase}


@pytest.fixture
def event_day_phase(
    peak_phase: OperationalPhase,
) -> EventDayPhase:
    return EventDayPhase(
        id=UUID("20000000-0000-0000-0000-000000000001"),
        event_day_id=UUID("30000000-0000-0000-0000-000000000001"),
        operational_phase_id=peak_phase.id,
        start_min=840,
        end_min=1080,
    )


@pytest.fixture
def event_day(
    event_day_phase: EventDayPhase,
    peak_phase: OperationalPhase,
) -> EventDay:
    return EventDay(
        id=UUID("40000000-0000-0000-0000-000000000001"),
        event_date=date(2026, 7, 15),
        operational_profile_id=UUID("50000000-0000-0000-0000-000000000001"),
        attendance_level_id=UUID("60000000-0000-0000-0000-000000000001"),
        operational_start_min=840,
        operational_end_min=1080,
        phases=(event_day_phase,),
    )


@pytest.fixture
def parking_type() -> UUID:
    return UUID("a0000000-0000-0000-0000-000000000001")


@pytest.fixture
def gastronomy_type() -> UUID:
    return UUID("b0000000-0000-0000-0000-000000000001")


@pytest.fixture
def zone_a(parking_type: UUID) -> Zone:
    return Zone(
        id=UUID("a0000000-0000-0000-0000-000000000001"),
        name="Parking Norte",
        zone_type_id=parking_type,
        capacity=500,
    )


@pytest.fixture
def zone_b(gastronomy_type: UUID) -> Zone:
    return Zone(
        id=UUID("a0000000-0000-0000-0000-000000000002"),
        name="Sector Gastronomico",
        zone_type_id=gastronomy_type,
        capacity=2000,
    )


@pytest.fixture
def zones(
    zone_a: Zone,
    zone_b: Zone,
) -> list[Zone]:
    return [zone_a, zone_b]


@pytest.fixture
def parking_behavior(
    peak_phase: OperationalPhase,
    parking_type: UUID,
) -> ZoneBehavior:
    return ZoneBehavior(
        id=UUID("b0000000-0000-0000-0000-000000000100"),
        zone_type_id=parking_type,
        operational_phase_id=peak_phase.id,
        density_factor=0.8,
        flow_restriction=FlowRestriction.REGULATED,
    )


@pytest.fixture
def gastronomy_behavior(
    peak_phase: OperationalPhase,
    gastronomy_type: UUID,
) -> ZoneBehavior:
    return ZoneBehavior(
        id=UUID("b0000000-0000-0000-0000-000000000200"),
        zone_type_id=gastronomy_type,
        operational_phase_id=peak_phase.id,
        density_factor=0.6,
        flow_restriction=FlowRestriction.OPEN,
    )


@pytest.fixture
def zone_behaviors(
    parking_behavior: ZoneBehavior,
    gastronomy_behavior: ZoneBehavior,
) -> dict[tuple[UUID, UUID], ZoneBehavior]:
    return {
        (parking_behavior.zone_type_id, parking_behavior.operational_phase_id): parking_behavior,
        (gastronomy_behavior.zone_type_id, gastronomy_behavior.operational_phase_id): gastronomy_behavior,
    }


@pytest.fixture
def normal_attendance() -> AttendanceLevel:
    return AttendanceLevel(
        id=UUID("60000000-0000-0000-0000-000000000001"),
        name="Normal",
        multiplier=1.0,
    )


class TestFullPipeline:
    def test_pipeline_returns_territorial_prediction(
        self,
        engine: ContextEngine,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        operational_phases: dict[UUID, OperationalPhase],
        normal_attendance: AttendanceLevel,
        event_day: EventDay,
    ) -> None:
        result = engine.predict(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            operational_phases=operational_phases,
            attendance_level=normal_attendance,
            event_day=event_day,
            events=[],
        )
        assert isinstance(result, TerritorialPrediction)

    def test_pipeline_without_events(
        self,
        engine: ContextEngine,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        operational_phases: dict[UUID, OperationalPhase],
        normal_attendance: AttendanceLevel,
        event_day: EventDay,
    ) -> None:
        result = engine.predict(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            operational_phases=operational_phases,
            attendance_level=normal_attendance,
            event_day=event_day,
            events=[],
        )
        assert result.timestamp == timestamp
        assert result.active_phase_id == UUID("10000000-0000-0000-0000-000000000001")
        assert result.active_event_day_phase_id == UUID("20000000-0000-0000-0000-000000000001")
        assert len(result.zone_states) == 2

    def test_pipeline_with_events(
        self,
        engine: ContextEngine,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        operational_phases: dict[UUID, OperationalPhase],
        normal_attendance: AttendanceLevel,
        event_day: EventDay,
    ) -> None:
        events = [
            OperationalEvent(
                target_zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
                impact_value=-50,
                is_incident=False,
                start_timestamp=datetime(2026, 7, 15, 14, 0),
                end_timestamp=datetime(2026, 7, 15, 16, 0),
            ),
        ]
        result = engine.predict(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            operational_phases=operational_phases,
            attendance_level=normal_attendance,
            event_day=event_day,
            events=events,
        )
        assert len(result.zone_states) == 2
        zone_a_state = next(s for s in result.zone_states if str(s.zone_id).endswith("0001"))
        zone_b_state = next(s for s in result.zone_states if str(s.zone_id).endswith("0002"))
        assert zone_a_state.confidence == 0.8
        assert zone_b_state.confidence == 1.0

    def test_pipeline_zone_states_values(
        self,
        engine: ContextEngine,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        operational_phases: dict[UUID, OperationalPhase],
        normal_attendance: AttendanceLevel,
        event_day: EventDay,
    ) -> None:
        result = engine.predict(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            operational_phases=operational_phases,
            attendance_level=normal_attendance,
            event_day=event_day,
            events=[],
        )
        zone_a_state = next(s for s in result.zone_states if str(s.zone_id).endswith("0001"))
        zone_b_state = next(s for s in result.zone_states if str(s.zone_id).endswith("0002"))

        assert zone_a_state.saturation_level == pytest.approx(400 / 500.0)
        assert zone_a_state.availability == 100
        assert zone_a_state.operational_state == "REGULATED"

        assert zone_b_state.saturation_level == pytest.approx(1200 / 2000.0)
        assert zone_b_state.availability == 800
        assert zone_b_state.operational_state == "MODERATE"

    def test_deterministic_output(
        self,
        engine: ContextEngine,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        operational_phases: dict[UUID, OperationalPhase],
        normal_attendance: AttendanceLevel,
        event_day: EventDay,
    ) -> None:
        events = [
            OperationalEvent(
                target_zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
                impact_value=-30,
                is_incident=False,
                start_timestamp=datetime(2026, 7, 15, 14, 0),
                end_timestamp=datetime(2026, 7, 15, 16, 0),
            ),
        ]
        r1 = engine.predict(
            timestamp=timestamp, zones=zones, zone_behaviors=zone_behaviors,
            operational_phases=operational_phases, attendance_level=normal_attendance,
            event_day=event_day, events=events,
        )
        r2 = engine.predict(
            timestamp=timestamp, zones=zones, zone_behaviors=zone_behaviors,
            operational_phases=operational_phases, attendance_level=normal_attendance,
            event_day=event_day, events=events,
        )
        assert r1.timestamp == r2.timestamp
        assert len(r1.zone_states) == len(r2.zone_states)
        for s1, s2 in zip(r1.zone_states, r2.zone_states):
            assert s1.saturation_level == s2.saturation_level
            assert s1.availability == s2.availability
            assert s1.operational_state == s2.operational_state
            assert s1.confidence == s2.confidence
            assert s1.reasoning_factors == s2.reasoning_factors


class TestErrorPropagation:
    def test_phase_not_found_propagates(
        self,
        engine: ContextEngine,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        operational_phases: dict[UUID, OperationalPhase],
        normal_attendance: AttendanceLevel,
    ) -> None:
        event_day_phase = EventDayPhase(
            id=UUID("20000000-0000-0000-0000-000000000001"),
            event_day_id=UUID("30000000-0000-0000-0000-000000000001"),
            operational_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
            start_min=0,
            end_min=100,
        )
        event_day = EventDay(
            event_date=date(2026, 7, 15),
            operational_profile_id=UUID("50000000-0000-0000-0000-000000000001"),
            attendance_level_id=UUID("60000000-0000-0000-0000-000000000001"),
            operational_start_min=0,
            operational_end_min=100,
            phases=(event_day_phase,),
        )
        with pytest.raises(InvalidPhaseContext):
            engine.predict(
                timestamp=timestamp, zones=zones, zone_behaviors=zone_behaviors,
                operational_phases=operational_phases, attendance_level=normal_attendance,
                event_day=event_day, events=[],
            )

    def test_behavior_not_found_propagates(
        self,
        engine: ContextEngine,
        timestamp: datetime,
        zones: list[Zone],
        operational_phases: dict[UUID, OperationalPhase],
        normal_attendance: AttendanceLevel,
        event_day: EventDay,
    ) -> None:
        with pytest.raises(BehaviorNotDefined):
            engine.predict(
                timestamp=timestamp, zones=zones, zone_behaviors={},
                operational_phases=operational_phases, attendance_level=normal_attendance,
                event_day=event_day, events=[],
            )
