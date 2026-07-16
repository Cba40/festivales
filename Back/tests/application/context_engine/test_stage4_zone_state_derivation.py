from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID

import pytest

from src.application.context_engine.dto import (
    EventEvaluationResult,
    ZoneApplication,
    ZoneBehaviorApplicationResult,
)
from src.application.context_engine.stage4_config import Stage4Config
from src.application.context_engine.stage4_zone_state_derivation import (
    derive_zone_states,
)
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_event import OperationalEvent
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.value_objects.zone_state import ZoneState


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
def zone_a() -> Zone:
    return Zone(
        id=UUID("a0000000-0000-0000-0000-000000000001"),
        name="Parking Norte",
        zone_type_id=UUID("10000000-0000-0000-0000-000000000001"),
        capacity=500,
    )


@pytest.fixture
def zone_b() -> Zone:
    return Zone(
        id=UUID("a0000000-0000-0000-0000-000000000002"),
        name="Sector Gastronomico",
        zone_type_id=UUID("10000000-0000-0000-0000-000000000002"),
        capacity=2000,
    )


@pytest.fixture
def zone_c() -> Zone:
    return Zone(
        id=UUID("a0000000-0000-0000-0000-000000000003"),
        name="Parking Sur",
        zone_type_id=UUID("10000000-0000-0000-0000-000000000001"),
        capacity=300,
    )


@pytest.fixture
def default_config() -> Stage4Config:
    return Stage4Config(
        saturation_high_threshold=0.9,
        saturation_moderate_threshold=0.5,
        confidence_no_events=1.0,
        confidence_planned_events=0.8,
        confidence_incident=0.5,
        wait_time_mapping=[
            (0.0, 0.3, 0),
            (0.3, 0.5, 5),
            (0.5, 0.7, 10),
            (0.7, 0.9, 15),
            (0.9, 1.01, 20),
        ],
    )


def _build_stage3_result(
    peak_phase: OperationalPhase,
    active_day_phase: EventDayPhase,
    timestamp: datetime,
    applications: Mapping[UUID, tuple[int, FlowRestriction]],
) -> ZoneBehaviorApplicationResult:
    zone_apps: dict[UUID, ZoneApplication] = {}
    for zid, (density, restriction) in applications.items():
        zone_apps[zid] = ZoneApplication(
            zone_id=zid,
            projected_density=density,
            active_restriction=restriction,
        )
    return ZoneBehaviorApplicationResult(
        active_operational_phase=peak_phase,
        active_event_day_phase=active_day_phase,
        timestamp=timestamp,
        zone_applications=zone_apps,
    )


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


class TestSaturationLevel:
    def test_exact_capacity_returns_one(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (500, FlowRestriction.OPEN)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert states[0].saturation_level == 1.0

    def test_half_capacity_returns_point_five(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_b: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_b.id: (1000, FlowRestriction.OPEN)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_b], [], evaluation_result, default_config
        )
        assert states[0].saturation_level == 0.5

    def test_empty_returns_zero(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (0, FlowRestriction.OPEN)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert states[0].saturation_level == 0.0


class TestAvailability:
    def test_remaining_capacity(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (350, FlowRestriction.OPEN)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert states[0].availability == 150

    def test_over_capacity_returns_zero(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (600, FlowRestriction.OPEN)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert states[0].availability == 0


class TestOperationalState:
    def test_closed_restriction(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (100, FlowRestriction.CLOSED)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert states[0].operational_state == "CLOSED"

    def test_regulated_restriction(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (100, FlowRestriction.REGULATED)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert states[0].operational_state == "REGULATED"

    def test_open_high_saturation(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (480, FlowRestriction.OPEN)},  # 480/500 = 0.96 >= 0.9
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert states[0].operational_state == "HIGH_DEMAND"

    def test_open_moderate_saturation(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (300, FlowRestriction.OPEN)},  # 300/500 = 0.6 >= 0.5
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert states[0].operational_state == "MODERATE"

    def test_open_low_saturation(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (100, FlowRestriction.OPEN)},  # 100/500 = 0.2 < 0.5
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert states[0].operational_state == "LOW_DEMAND"


class TestEstimatedWait:
    def test_low_saturation_no_wait(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (50, FlowRestriction.OPEN)},  # 50/500 = 0.1
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert states[0].estimated_wait == 0

    def test_high_saturation_max_wait(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (500, FlowRestriction.OPEN)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert states[0].estimated_wait == 20

    def test_configurable_mapping(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
    ) -> None:
        custom_config = Stage4Config(
            wait_time_mapping=[(0.0, 1.0, 99)],
        )
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (250, FlowRestriction.OPEN)},  # 250/500 = 0.5
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, custom_config
        )
        assert states[0].estimated_wait == 99


class TestConfidence:
    def test_no_events_max_confidence(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (250, FlowRestriction.OPEN)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert states[0].confidence == 1.0

    def test_planned_event_reduces_confidence(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (250, FlowRestriction.OPEN)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        active_events = [
            OperationalEvent(
                target_zone_id=zone_a.id,
                impact_value=-30,
                is_incident=False,
                start_timestamp=timestamp,
                end_timestamp=datetime(2026, 7, 15, 16, 0),
            )
        ]
        states = derive_zone_states(
            stage3_result, [zone_a], active_events, evaluation_result, default_config
        )
        assert states[0].confidence == 0.8

    def test_incident_lowest_confidence(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (250, FlowRestriction.OPEN)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        active_events = [
            OperationalEvent(
                target_zone_id=zone_a.id,
                impact_value=-80,
                is_incident=True,
                start_timestamp=timestamp,
                end_timestamp=datetime(2026, 7, 15, 16, 0),
            )
        ]
        states = derive_zone_states(
            stage3_result, [zone_a], active_events, evaluation_result, default_config
        )
        assert states[0].confidence == 0.5

    def test_configurable_confidence_values(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
    ) -> None:
        custom_config = Stage4Config(
            confidence_no_events=0.95,
            confidence_planned_events=0.75,
            confidence_incident=0.4,
        )
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (250, FlowRestriction.OPEN)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, custom_config
        )
        assert states[0].confidence == 0.95


class TestReasoningFactors:
    def test_impact_reasoning(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (250, FlowRestriction.OPEN)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: -50},
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert any("Impacto de evento operativo: -50" in f for f in states[0].reasoning_factors)

    def test_incident_reasoning(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (250, FlowRestriction.OPEN)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        active_events = [
            OperationalEvent(
                target_zone_id=zone_a.id,
                impact_value=-100,
                is_incident=True,
                start_timestamp=timestamp,
                end_timestamp=datetime(2026, 7, 15, 16, 0),
            )
        ]
        states = derive_zone_states(
            stage3_result, [zone_a], active_events, evaluation_result, default_config
        )
        assert any("Incidente activo en zona" in f for f in states[0].reasoning_factors)

    def test_high_saturation_reasoning(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (500, FlowRestriction.OPEN)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert any("Alta saturación proyectada" in f for f in states[0].reasoning_factors)

    def test_regulated_reasoning(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (250, FlowRestriction.REGULATED)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert any("Acceso regulado" in f for f in states[0].reasoning_factors)

    def test_closed_reasoning(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (0, FlowRestriction.CLOSED)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert any("Zona cerrada" in f for f in states[0].reasoning_factors)


class TestMultiZone:
    def test_all_zones_have_state(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        zone_b: Zone,
        zone_c: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {
                zone_a.id: (400, FlowRestriction.REGULATED),
                zone_b.id: (1200, FlowRestriction.OPEN),
                zone_c.id: (50, FlowRestriction.OPEN),
            },
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a, zone_b, zone_c], [], evaluation_result, default_config
        )
        assert len(states) == 3
        state_map = {s.zone_id: s for s in states}
        assert zone_a.id in state_map
        assert zone_b.id in state_map
        assert zone_c.id in state_map

    def test_mixed_restrictions_and_impacts(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        zone_b: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {
                zone_a.id: (350, FlowRestriction.REGULATED),
                zone_b.id: (1800, FlowRestriction.CLOSED),
            },
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: -50},
        )
        active_events = [
            OperationalEvent(
                target_zone_id=zone_a.id,
                impact_value=-50,
                is_incident=False,
                start_timestamp=timestamp,
                end_timestamp=datetime(2026, 7, 15, 16, 0),
            ),
            OperationalEvent(
                target_zone_id=zone_b.id,
                impact_value=-100,
                is_incident=True,
                start_timestamp=timestamp,
                end_timestamp=datetime(2026, 7, 15, 16, 0),
            ),
        ]
        states = derive_zone_states(
            stage3_result, [zone_a, zone_b], active_events, evaluation_result, default_config
        )
        state_map = {s.zone_id: s for s in states}

        s_a = state_map[zone_a.id]
        assert s_a.operational_state == "REGULATED"
        assert s_a.saturation_level == pytest.approx(350 / 500.0)
        assert s_a.availability == 150
        assert s_a.confidence == 0.8
        assert any("Impacto de evento operativo: -50" in f for f in s_a.reasoning_factors)

        s_b = state_map[zone_b.id]
        assert s_b.operational_state == "CLOSED"
        assert s_b.saturation_level == pytest.approx(1800 / 2000.0)
        assert s_b.availability == 200
        assert s_b.confidence == 0.5
        assert any("Zona cerrada" in f for f in s_b.reasoning_factors)
        assert any("Incidente activo en zona" in f for f in s_b.reasoning_factors)


class TestEmptyInput:
    def test_no_zones_returns_empty(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp, {}
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [], [], evaluation_result, default_config
        )
        assert len(states) == 0


class TestOutputType:
    def test_returns_zone_state_objects(
        self,
        peak_phase: OperationalPhase,
        active_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_a: Zone,
        default_config: Stage4Config,
    ) -> None:
        stage3_result = _build_stage3_result(
            peak_phase, active_day_phase, timestamp,
            {zone_a.id: (250, FlowRestriction.OPEN)},
        )
        evaluation_result = _make_evaluation_result(
            peak_phase, active_day_phase, timestamp
        )
        states = derive_zone_states(
            stage3_result, [zone_a], [], evaluation_result, default_config
        )
        assert isinstance(states[0], ZoneState)
