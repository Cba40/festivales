from datetime import datetime
from uuid import UUID

import pytest

from src.application.context_engine.stage5_prediction_assembly import (
    assemble_prediction,
)
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState


@pytest.fixture
def timestamp() -> datetime:
    return datetime(2026, 7, 15, 15, 0)


@pytest.fixture
def phase() -> OperationalPhase:
    return OperationalPhase(
        id=UUID("10000000-0000-0000-0000-000000000001"),
        name="Peak",
        sequence_order=2,
    )


@pytest.fixture
def event_day_phase() -> EventDayPhase:
    return EventDayPhase(
        id=UUID("20000000-0000-0000-0000-000000000001"),
        event_day_id=UUID("30000000-0000-0000-0000-000000000001"),
        operational_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
        start_min=840,
        end_min=1080,
    )


@pytest.fixture
def zone_a_state() -> ZoneState:
    return ZoneState(
        zone_id=UUID("a0000000-0000-0000-0000-000000000001"),
        operational_state="REGULATED",
        availability=150,
        saturation_level=0.7,
        estimated_wait=10,
        confidence=1.0,
        reasoning_factors=[],
        active_restriction=FlowRestriction.REGULATED,
    )


@pytest.fixture
def zone_b_state() -> ZoneState:
    return ZoneState(
        zone_id=UUID("a0000000-0000-0000-0000-000000000002"),
        operational_state="OPEN",
        availability=800,
        saturation_level=0.6,
        estimated_wait=10,
        confidence=0.8,
        reasoning_factors=["Impacto de evento operativo: -30"],
        active_restriction=FlowRestriction.OPEN,
    )


class TestOutputType:
    def test_returns_territorial_prediction(
        self,
        timestamp: datetime,
        phase: OperationalPhase,
        event_day_phase: EventDayPhase,
        zone_a_state: ZoneState,
    ) -> None:
        result = assemble_prediction(
            [zone_a_state], phase, event_day_phase, timestamp
        )
        assert isinstance(result, TerritorialPrediction)


class TestEmptyZones:
    def test_empty_zone_states_allowed(
        self,
        timestamp: datetime,
        phase: OperationalPhase,
        event_day_phase: EventDayPhase,
    ) -> None:
        result = assemble_prediction([], phase, event_day_phase, timestamp)
        assert len(result.zone_states) == 0


class TestSingleZone:
    def test_single_zone_preserved(
        self,
        timestamp: datetime,
        phase: OperationalPhase,
        event_day_phase: EventDayPhase,
        zone_a_state: ZoneState,
    ) -> None:
        result = assemble_prediction(
            [zone_a_state], phase, event_day_phase, timestamp
        )
        assert len(result.zone_states) == 1
        assert result.zone_states[0] is zone_a_state


class TestMultipleZones:
    def test_multiple_zones_preserved(
        self,
        timestamp: datetime,
        phase: OperationalPhase,
        event_day_phase: EventDayPhase,
        zone_a_state: ZoneState,
        zone_b_state: ZoneState,
    ) -> None:
        result = assemble_prediction(
            [zone_a_state, zone_b_state], phase, event_day_phase, timestamp
        )
        assert len(result.zone_states) == 2
        assert result.zone_states[0] is zone_a_state
        assert result.zone_states[1] is zone_b_state


class TestMetadata:
    def test_preserves_timestamp(
        self,
        timestamp: datetime,
        phase: OperationalPhase,
        event_day_phase: EventDayPhase,
        zone_a_state: ZoneState,
    ) -> None:
        result = assemble_prediction(
            [zone_a_state], phase, event_day_phase, timestamp
        )
        assert result.timestamp == timestamp

    def test_preserves_active_phase_id(
        self,
        timestamp: datetime,
        phase: OperationalPhase,
        event_day_phase: EventDayPhase,
        zone_a_state: ZoneState,
    ) -> None:
        result = assemble_prediction(
            [zone_a_state], phase, event_day_phase, timestamp
        )
        assert result.active_phase_id == phase.id

    def test_preserves_active_event_day_phase_id(
        self,
        timestamp: datetime,
        phase: OperationalPhase,
        event_day_phase: EventDayPhase,
        zone_a_state: ZoneState,
    ) -> None:
        result = assemble_prediction(
            [zone_a_state], phase, event_day_phase, timestamp
        )
        assert result.active_event_day_phase_id == event_day_phase.id


class TestImmutability:
    def test_zone_states_list_copy_on_read(
        self,
        timestamp: datetime,
        phase: OperationalPhase,
        event_day_phase: EventDayPhase,
        zone_a_state: ZoneState,
        zone_b_state: ZoneState,
    ) -> None:
        result = assemble_prediction(
            [zone_a_state, zone_b_state], phase, event_day_phase, timestamp
        )
        external = result.zone_states
        external.append(zone_a_state)
        assert len(result.zone_states) == 2

    def test_zone_states_list_copy_on_write(
        self,
        timestamp: datetime,
        phase: OperationalPhase,
        event_day_phase: EventDayPhase,
        zone_a_state: ZoneState,
        zone_b_state: ZoneState,
    ) -> None:
        result = assemble_prediction(
            [zone_a_state, zone_b_state], phase, event_day_phase, timestamp
        )
        internal = result.zone_states
        assert internal is not result.zone_states
