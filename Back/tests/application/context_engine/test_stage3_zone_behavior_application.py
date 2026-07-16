from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID

import pytest

from src.application.context_engine.dto import (
    EventEvaluationResult,
    ZoneApplication,
    ZoneBehaviorApplicationResult,
)
from src.application.context_engine.exceptions import BehaviorNotDefined
from src.application.context_engine.stage3_zone_behavior_application import (
    apply_zone_behaviors,
)
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction, ZoneBehavior


@pytest.fixture
def peak_phase() -> OperationalPhase:
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
def timestamp() -> datetime:
    return datetime(2026, 7, 15, 15, 0)


@pytest.fixture
def normal_attendance() -> AttendanceLevel:
    return AttendanceLevel(name="Normal", multiplier=1.0)


@pytest.fixture
def low_attendance() -> AttendanceLevel:
    return AttendanceLevel(name="Low", multiplier=0.5)


@pytest.fixture
def high_attendance() -> AttendanceLevel:
    return AttendanceLevel(name="High", multiplier=1.5)


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
def zone_c(parking_type: UUID) -> Zone:
    return Zone(
        id=UUID("a0000000-0000-0000-0000-000000000003"),
        name="Parking Sur",
        zone_type_id=parking_type,
        capacity=300,
    )


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
) -> Mapping[tuple[UUID, UUID], ZoneBehavior]:
    return {
        (parking_behavior.zone_type_id, parking_behavior.operational_phase_id): parking_behavior,
        (gastronomy_behavior.zone_type_id, gastronomy_behavior.operational_phase_id): gastronomy_behavior,
    }


def _make_evaluation_result(
    peak_phase: OperationalPhase,
    active_day_phase: EventDayPhase,
    timestamp: datetime,
    impacts: Mapping[UUID, int] | None = None,
) -> EventEvaluationResult:
    return EventEvaluationResult(
        active_operational_phase=peak_phase,
        active_event_day_phase=active_day_phase,
        timestamp=timestamp,
        event_impacts=impacts or {},
    )


class TestDensityCalculation:
    def test_computes_projected_density_from_capacity_multiplier_factor(
        self,
        zone_a: Zone,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        normal_attendance: AttendanceLevel,
    ) -> None:
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        result = apply_zone_behaviors(
            zones=[zone_a],
            zone_behaviors=zone_behaviors,
            attendance_level=normal_attendance,
            evaluation_result=evaluation_result,
        )

        app = result.zone_applications[zone_a.id]
        # capacity=500, multiplier=1.0, density_factor=0.8 -> round(400) = 400
        assert app.projected_density == 400

    def test_applies_attendance_level_multiplier(
        self,
        zone_a: Zone,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        low_attendance: AttendanceLevel,
    ) -> None:
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        result = apply_zone_behaviors(
            zones=[zone_a],
            zone_behaviors=zone_behaviors,
            attendance_level=low_attendance,
            evaluation_result=evaluation_result,
        )

        app = result.zone_applications[zone_a.id]
        # capacity=500, multiplier=0.5, density_factor=0.8 -> round(200) = 200
        assert app.projected_density == 200

    def test_rounds_to_nearest_integer(
        self,
        zone_a: Zone,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        high_attendance: AttendanceLevel,
    ) -> None:
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        result = apply_zone_behaviors(
            zones=[zone_a],
            zone_behaviors=zone_behaviors,
            attendance_level=high_attendance,
            evaluation_result=evaluation_result,
        )

        app = result.zone_applications[zone_a.id]
        # capacity=500, multiplier=1.5, density_factor=0.8 -> round(600) = 600
        assert app.projected_density == 600


class TestImpactAddition:
    def test_adds_accumulated_impact_to_projected_density(
        self,
        zone_b: Zone,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        normal_attendance: AttendanceLevel,
    ) -> None:
        impacts = {zone_b.id: -50}
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp, impacts
        )
        result = apply_zone_behaviors(
            zones=[zone_b],
            zone_behaviors=zone_behaviors,
            attendance_level=normal_attendance,
            evaluation_result=evaluation_result,
        )

        app = result.zone_applications[zone_b.id]
        # capacity=2000, multiplier=1.0, density_factor=0.6 -> round(1200) = 1200
        # accumulated_impact = -50 -> 1200 + (-50) = 1150
        assert app.projected_density == 1150

    def test_defaults_impact_to_zero_when_zone_missing(
        self,
        zone_b: Zone,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        normal_attendance: AttendanceLevel,
    ) -> None:
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        result = apply_zone_behaviors(
            zones=[zone_b],
            zone_behaviors=zone_behaviors,
            attendance_level=normal_attendance,
            evaluation_result=evaluation_result,
        )

        app = result.zone_applications[zone_b.id]
        # capacity=2000, multiplier=1.0, density_factor=0.6 -> round(1200) = 1200
        # no impact -> default 0 -> 1200
        assert app.projected_density == 1200


class TestClamping:
    def test_clamps_projected_density_to_zero_when_negative(
        self,
        zone_c: Zone,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        low_attendance: AttendanceLevel,
    ) -> None:
        impacts = {zone_c.id: -200}
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp, impacts
        )
        result = apply_zone_behaviors(
            zones=[zone_c],
            zone_behaviors=zone_behaviors,
            attendance_level=low_attendance,
            evaluation_result=evaluation_result,
        )

        app = result.zone_applications[zone_c.id]
        # capacity=300, multiplier=0.5, density_factor=0.8 -> round(120) = 120
        # impact = -200 -> -80 -> clamped to 0
        assert app.projected_density == 0

    def test_keeps_positive_density_unchanged(
        self,
        zone_a: Zone,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        normal_attendance: AttendanceLevel,
    ) -> None:
        impacts = {zone_a.id: -30}
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp, impacts
        )
        result = apply_zone_behaviors(
            zones=[zone_a],
            zone_behaviors=zone_behaviors,
            attendance_level=normal_attendance,
            evaluation_result=evaluation_result,
        )

        app = result.zone_applications[zone_a.id]
        # capacity=500, multiplier=1.0, density_factor=0.8 -> round(400) = 400
        # impact = -30 -> 370 (still positive, not clamped)
        assert app.projected_density == 370


class TestActiveRestriction:
    def test_uses_behavior_flow_restriction_by_default(
        self,
        zone_a: Zone,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        normal_attendance: AttendanceLevel,
        parking_behavior: ZoneBehavior,
    ) -> None:
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        result = apply_zone_behaviors(
            zones=[zone_a],
            zone_behaviors=zone_behaviors,
            attendance_level=normal_attendance,
            evaluation_result=evaluation_result,
        )

        app = result.zone_applications[zone_a.id]
        assert app.active_restriction == parking_behavior.flow_restriction

    def test_overrides_to_closed_when_impact_at_negative_threshold(
        self,
        zone_a: Zone,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        normal_attendance: AttendanceLevel,
    ) -> None:
        impacts = {zone_a.id: -100}
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp, impacts
        )
        result = apply_zone_behaviors(
            zones=[zone_a],
            zone_behaviors=zone_behaviors,
            attendance_level=normal_attendance,
            evaluation_result=evaluation_result,
        )

        app = result.zone_applications[zone_a.id]
        assert app.active_restriction == FlowRestriction.CLOSED

    def test_overrides_to_closed_when_impact_below_threshold(
        self,
        zone_a: Zone,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        normal_attendance: AttendanceLevel,
    ) -> None:
        impacts = {zone_a.id: -150}
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp, impacts
        )
        result = apply_zone_behaviors(
            zones=[zone_a],
            zone_behaviors=zone_behaviors,
            attendance_level=normal_attendance,
            evaluation_result=evaluation_result,
        )

        app = result.zone_applications[zone_a.id]
        assert app.active_restriction == FlowRestriction.CLOSED


class TestBehaviorNotFound:
    def test_raises_error_when_behavior_missing(
        self,
        zone_a: Zone,
        zone_b: Zone,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        normal_attendance: AttendanceLevel,
    ) -> None:
        limited_behaviors = {
            k: v
            for k, v in zone_behaviors.items()
            if v.zone_type_id != zone_b.zone_type_id
        }
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )

        with pytest.raises(BehaviorNotDefined) as exc_info:
            apply_zone_behaviors(
                zones=[zone_a, zone_b],
                zone_behaviors=limited_behaviors,
                attendance_level=normal_attendance,
                evaluation_result=evaluation_result,
            )

        assert "BEHAVIOR_NOT_DEFINED" in str(exc_info.value)


class TestMultiZone:
    def test_different_zones_get_correct_projections(
        self,
        zone_a: Zone,
        zone_b: Zone,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        normal_attendance: AttendanceLevel,
        parking_behavior: ZoneBehavior,
        gastronomy_behavior: ZoneBehavior,
    ) -> None:
        impacts = {zone_b.id: -100}
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp, impacts
        )
        result = apply_zone_behaviors(
            zones=[zone_a, zone_b],
            zone_behaviors=zone_behaviors,
            attendance_level=normal_attendance,
            evaluation_result=evaluation_result,
        )

        assert len(result.zone_applications) == 2

        app_a = result.zone_applications[zone_a.id]
        # capacity=500, mult=1.0, factor=0.8 -> round(400) = 400, impact=0 -> 400
        assert app_a.projected_density == 400
        assert app_a.active_restriction == parking_behavior.flow_restriction  # REGULATED

        app_b = result.zone_applications[zone_b.id]
        # capacity=2000, mult=1.0, factor=0.6 -> round(1200) = 1200, impact=-100 -> 1100
        assert app_b.projected_density == 1100
        assert app_b.active_restriction == FlowRestriction.CLOSED  # overridden

    def test_empty_zones_returns_empty_applications(
        self,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        normal_attendance: AttendanceLevel,
    ) -> None:
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        result = apply_zone_behaviors(
            zones=[],
            zone_behaviors=zone_behaviors,
            attendance_level=normal_attendance,
            evaluation_result=evaluation_result,
        )

        assert len(result.zone_applications) == 0

    def test_same_zone_type_different_capacities(
        self,
        zone_a: Zone,
        zone_c: Zone,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        normal_attendance: AttendanceLevel,
    ) -> None:
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        result = apply_zone_behaviors(
            zones=[zone_a, zone_c],
            zone_behaviors=zone_behaviors,
            attendance_level=normal_attendance,
            evaluation_result=evaluation_result,
        )

        assert len(result.zone_applications) == 2

        app_a = result.zone_applications[zone_a.id]
        assert app_a.projected_density == 400  # capacity=500

        app_c = result.zone_applications[zone_c.id]
        assert app_c.projected_density == 240  # capacity=300


class TestResultMetadata:
    def test_preserves_phase_and_timestamp(
        self,
        zone_a: Zone,
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        normal_attendance: AttendanceLevel,
    ) -> None:
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        result = apply_zone_behaviors(
            zones=[zone_a],
            zone_behaviors=zone_behaviors,
            attendance_level=normal_attendance,
            evaluation_result=evaluation_result,
        )

        assert result.active_operational_phase is peak_phase
        assert result.active_event_day_phase is active_day_phase
        assert result.timestamp == timestamp

