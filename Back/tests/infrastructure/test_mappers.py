from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_event import OperationalEvent
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.operational_profile import OperationalProfile
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction, ZoneBehavior
from src.domain.entities.zone_type import ZoneType
from src.infrastructure.persistence.mappers import (
    attendance_level_to_domain,
    attendance_level_to_model,
    event_day_phase_to_domain,
    event_day_phase_to_model,
    event_day_to_domain,
    event_day_to_model,
    operational_event_to_domain,
    operational_event_to_model,
    operational_phase_to_domain,
    operational_phase_to_model,
    operational_profile_to_domain,
    operational_profile_to_model,
    zone_behavior_to_domain,
    zone_behavior_to_model,
    zone_to_domain,
    zone_to_model,
    zone_type_to_domain,
    zone_type_to_model,
)
from src.infrastructure.persistence.models import (
    AttendanceLevelModel,
    EventDayModel,
    EventDayPhaseModel,
    OperationalEventModel,
    OperationalPhaseModel,
    OperationalProfileModel,
    ZoneBehaviorModel,
    ZoneModel,
    ZoneTypeModel,
)

A_UUID = UUID("11111111-1111-1111-1111-111111111111")
B_UUID = UUID("22222222-2222-2222-2222-222222222222")
C_UUID = UUID("33333333-3333-3333-3333-333333333333")


# ---------------------------------------------------------------------------
# ZoneType
# ---------------------------------------------------------------------------


class TestZoneTypeMapper:
    def test_to_domain(self) -> None:
        model = ZoneTypeModel(id=A_UUID, name="TestType")
        entity = zone_type_to_domain(model)
        assert entity.id == A_UUID
        assert entity.name == "TestType"
        assert isinstance(entity, ZoneType)

    def test_to_model(self) -> None:
        entity = ZoneType(id=A_UUID, name="TestType")
        model = zone_type_to_model(entity)
        assert model.id == A_UUID
        assert model.name == "TestType"
        assert isinstance(model, ZoneTypeModel)

    def test_round_trip(self) -> None:
        original = ZoneType(id=A_UUID, name="TestType")
        model = zone_type_to_model(original)
        result = zone_type_to_domain(model)
        assert result.id == original.id
        assert result.name == original.name


# ---------------------------------------------------------------------------
# Zone
# ---------------------------------------------------------------------------


class TestZoneMapper:
    def test_to_domain(self) -> None:
        model = ZoneModel(id=A_UUID, name="TestZone", zone_type_id=B_UUID, capacity=100)
        entity = zone_to_domain(model)
        assert entity.id == A_UUID
        assert entity.name == "TestZone"
        assert entity.zone_type_id == B_UUID
        assert entity.capacity == 100
        assert isinstance(entity, Zone)

    def test_to_model(self) -> None:
        entity = Zone(id=A_UUID, name="TestZone", zone_type_id=B_UUID, capacity=100)
        model = zone_to_model(entity)
        assert model.id == A_UUID
        assert model.name == "TestZone"
        assert model.zone_type_id == B_UUID
        assert model.capacity == 100
        assert isinstance(model, ZoneModel)

    def test_round_trip(self) -> None:
        original = Zone(id=A_UUID, name="TestZone", zone_type_id=B_UUID, capacity=100)
        model = zone_to_model(original)
        result = zone_to_domain(model)
        assert result.id == original.id
        assert result.name == original.name
        assert result.zone_type_id == original.zone_type_id
        assert result.capacity == original.capacity


# ---------------------------------------------------------------------------
# AttendanceLevel
# ---------------------------------------------------------------------------


class TestAttendanceLevelMapper:
    def test_to_domain(self) -> None:
        model = AttendanceLevelModel(id=A_UUID, name="Bajo", multiplier=0.5)
        entity = attendance_level_to_domain(model)
        assert entity.id == A_UUID
        assert entity.name == "Bajo"
        assert entity.multiplier == 0.5
        assert isinstance(entity, AttendanceLevel)

    def test_to_model(self) -> None:
        entity = AttendanceLevel(id=A_UUID, name="Bajo", multiplier=0.5)
        model = attendance_level_to_model(entity)
        assert model.id == A_UUID
        assert model.name == "Bajo"
        assert model.multiplier == 0.5
        assert isinstance(model, AttendanceLevelModel)

    def test_round_trip(self) -> None:
        original = AttendanceLevel(id=A_UUID, name="Bajo", multiplier=0.5)
        model = attendance_level_to_model(original)
        result = attendance_level_to_domain(model)
        assert result.id == original.id
        assert result.name == original.name
        assert result.multiplier == original.multiplier


# ---------------------------------------------------------------------------
# OperationalPhase
# ---------------------------------------------------------------------------


class TestOperationalPhaseMapper:
    def test_to_domain(self) -> None:
        model = OperationalPhaseModel(id=A_UUID, name="Apertura", sequence_order=1)
        entity = operational_phase_to_domain(model)
        assert entity.id == A_UUID
        assert entity.name == "Apertura"
        assert entity.sequence_order == 1
        assert isinstance(entity, OperationalPhase)

    def test_to_model(self) -> None:
        entity = OperationalPhase(id=A_UUID, name="Apertura", sequence_order=1)
        model = operational_phase_to_model(entity)
        assert model.id == A_UUID
        assert model.name == "Apertura"
        assert model.sequence_order == 1
        assert isinstance(model, OperationalPhaseModel)

    def test_round_trip(self) -> None:
        original = OperationalPhase(id=A_UUID, name="Apertura", sequence_order=1)
        model = operational_phase_to_model(original)
        result = operational_phase_to_domain(model)
        assert result.id == original.id
        assert result.name == original.name
        assert result.sequence_order == original.sequence_order


# ---------------------------------------------------------------------------
# ZoneBehavior
# ---------------------------------------------------------------------------


class TestZoneBehaviorMapper:
    def test_to_domain(self) -> None:
        model = ZoneBehaviorModel(
            id=A_UUID,
            zone_type_id=B_UUID,
            operational_phase_id=C_UUID,
            density_factor=0.75,
            flow_restriction=FlowRestriction.REGULATED,
        )
        entity = zone_behavior_to_domain(model)
        assert entity.id == A_UUID
        assert entity.zone_type_id == B_UUID
        assert entity.operational_phase_id == C_UUID
        assert entity.density_factor == 0.75
        assert entity.flow_restriction == FlowRestriction.REGULATED
        assert isinstance(entity, ZoneBehavior)

    def test_to_model(self) -> None:
        entity = ZoneBehavior(
            id=A_UUID,
            zone_type_id=B_UUID,
            operational_phase_id=C_UUID,
            density_factor=0.75,
            flow_restriction=FlowRestriction.REGULATED,
        )
        model = zone_behavior_to_model(entity)
        assert model.id == A_UUID
        assert model.zone_type_id == B_UUID
        assert model.operational_phase_id == C_UUID
        assert model.density_factor == 0.75
        assert model.flow_restriction == FlowRestriction.REGULATED
        assert isinstance(model, ZoneBehaviorModel)

    def test_round_trip(self) -> None:
        original = ZoneBehavior(
            id=A_UUID,
            zone_type_id=B_UUID,
            operational_phase_id=C_UUID,
            density_factor=0.75,
            flow_restriction=FlowRestriction.REGULATED,
        )
        model = zone_behavior_to_model(original)
        result = zone_behavior_to_domain(model)
        assert result.id == original.id
        assert result.zone_type_id == original.zone_type_id
        assert result.operational_phase_id == original.operational_phase_id
        assert result.density_factor == original.density_factor
        assert result.flow_restriction == original.flow_restriction

    def test_all_flow_restriction_values(self) -> None:
        for fr in FlowRestriction:
            entity = ZoneBehavior(
                id=A_UUID,
                zone_type_id=B_UUID,
                operational_phase_id=C_UUID,
                density_factor=0.5,
                flow_restriction=fr,
            )
            model = zone_behavior_to_model(entity)
            result = zone_behavior_to_domain(model)
            assert result.flow_restriction == fr


# ---------------------------------------------------------------------------
# EventDayPhase
# ---------------------------------------------------------------------------


class TestEventDayPhaseMapper:
    def test_to_domain(self) -> None:
        model = EventDayPhaseModel(
            id=A_UUID,
            event_day_id=B_UUID,
            operational_phase_id=C_UUID,
            start_min=480,
            end_min=720,
        )
        entity = event_day_phase_to_domain(model)
        assert entity.id == A_UUID
        assert entity.event_day_id == B_UUID
        assert entity.operational_phase_id == C_UUID
        assert entity.start_min == 480
        assert entity.end_min == 720
        assert isinstance(entity, EventDayPhase)

    def test_to_model(self) -> None:
        entity = EventDayPhase(
            id=A_UUID,
            event_day_id=B_UUID,
            operational_phase_id=C_UUID,
            start_min=480,
            end_min=720,
        )
        model = event_day_phase_to_model(entity)
        assert model.id == A_UUID
        assert model.event_day_id == B_UUID
        assert model.operational_phase_id == C_UUID
        assert model.start_min == 480
        assert model.end_min == 720
        assert isinstance(model, EventDayPhaseModel)

    def test_round_trip(self) -> None:
        original = EventDayPhase(
            id=A_UUID,
            event_day_id=B_UUID,
            operational_phase_id=C_UUID,
            start_min=480,
            end_min=720,
        )
        model = event_day_phase_to_model(original)
        result = event_day_phase_to_domain(model)
        assert result.id == original.id
        assert result.event_day_id == original.event_day_id
        assert result.operational_phase_id == original.operational_phase_id
        assert result.start_min == original.start_min
        assert result.end_min == original.end_min


# ---------------------------------------------------------------------------
# OperationalEvent
# ---------------------------------------------------------------------------


class TestOperationalEventMapper:
    def test_to_domain(self) -> None:
        start = datetime(2026, 7, 10, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)
        model = OperationalEventModel(
            id=A_UUID,
            target_zone_id=B_UUID,
            impact_value=-50,
            is_incident=True,
            start_timestamp=start,
            end_timestamp=end,
        )
        entity = operational_event_to_domain(model)
        assert entity.id == A_UUID
        assert entity.target_zone_id == B_UUID
        assert entity.impact_value == -50
        assert entity.is_incident is True
        assert entity.start_timestamp == start
        assert entity.end_timestamp == end
        assert isinstance(entity, OperationalEvent)

    def test_to_model(self) -> None:
        start = datetime(2026, 7, 10, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)
        entity = OperationalEvent(
            id=A_UUID,
            target_zone_id=B_UUID,
            impact_value=-50,
            is_incident=True,
            start_timestamp=start,
            end_timestamp=end,
        )
        model = operational_event_to_model(entity)
        assert model.id == A_UUID
        assert model.target_zone_id == B_UUID
        assert model.impact_value == -50
        assert model.is_incident is True
        assert model.start_timestamp == start
        assert model.end_timestamp == end
        assert isinstance(model, OperationalEventModel)

    def test_round_trip(self) -> None:
        start = datetime(2026, 7, 10, 10, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)
        original = OperationalEvent(
            id=A_UUID,
            target_zone_id=B_UUID,
            impact_value=-50,
            is_incident=True,
            start_timestamp=start,
            end_timestamp=end,
        )
        model = operational_event_to_model(original)
        result = operational_event_to_domain(model)
        assert result.id == original.id
        assert result.target_zone_id == original.target_zone_id
        assert result.impact_value == original.impact_value
        assert result.is_incident == original.is_incident
        assert result.start_timestamp == original.start_timestamp
        assert result.end_timestamp == original.end_timestamp


# ---------------------------------------------------------------------------
# OperationalProfile (aggregate with phases)
# ---------------------------------------------------------------------------


class TestOperationalProfileMapper:
    def test_to_domain(self) -> None:
        phase_a = OperationalPhaseModel(id=A_UUID, name="Apertura", sequence_order=1)
        phase_b = OperationalPhaseModel(id=B_UUID, name="Pico", sequence_order=2)
        model = OperationalProfileModel(id=C_UUID, name="Perfil Test")
        model.phases = [phase_a, phase_b]

        entity = operational_profile_to_domain(model)
        assert entity.id == C_UUID
        assert entity.name == "Perfil Test"
        assert len(entity.phases) == 2
        assert entity.phases[0].id == A_UUID
        assert entity.phases[0].name == "Apertura"
        assert entity.phases[0].sequence_order == 1
        assert entity.phases[1].id == B_UUID
        assert entity.phases[1].name == "Pico"
        assert entity.phases[1].sequence_order == 2
        assert isinstance(entity, OperationalProfile)

    def test_to_model(self) -> None:
        phase_a = OperationalPhase(id=A_UUID, name="Apertura", sequence_order=1)
        phase_b = OperationalPhase(id=B_UUID, name="Pico", sequence_order=2)
        entity = OperationalProfile(id=C_UUID, name="Perfil Test", phases=(phase_a, phase_b))

        model = operational_profile_to_model(entity)
        assert model.id == C_UUID
        assert model.name == "Perfil Test"
        assert len(model.phases) == 2
        assert model.phases[0].id == A_UUID
        assert model.phases[0].name == "Apertura"
        assert model.phases[0].sequence_order == 1
        assert model.phases[0].operational_profile_id == C_UUID
        assert model.phases[1].id == B_UUID
        assert model.phases[1].name == "Pico"
        assert model.phases[1].sequence_order == 2
        assert model.phases[1].operational_profile_id == C_UUID
        assert isinstance(model, OperationalProfileModel)

    def test_round_trip_preserves_all_data(self) -> None:
        phase_a = OperationalPhase(id=A_UUID, name="Apertura", sequence_order=1)
        phase_b = OperationalPhase(id=B_UUID, name="Pico", sequence_order=2)
        original = OperationalProfile(id=C_UUID, name="Perfil Test", phases=(phase_a, phase_b))

        model = operational_profile_to_model(original)
        result = operational_profile_to_domain(model)

        assert result.id == original.id
        assert result.name == original.name
        assert len(result.phases) == len(original.phases)
        for rp, op in zip(result.phases, original.phases):
            assert rp.id == op.id
            assert rp.name == op.name
            assert rp.sequence_order == op.sequence_order

    def test_to_model_sets_fk_on_phases(self) -> None:
        profile_id = uuid4()
        phase = OperationalPhase(id=uuid4(), name="Unica", sequence_order=1)
        entity = OperationalProfile(id=profile_id, name="Perfil", phases=(phase,))

        model = operational_profile_to_model(entity)
        for p in model.phases:
            assert p.operational_profile_id == profile_id


# ---------------------------------------------------------------------------
# EventDay (aggregate with phases)
# ---------------------------------------------------------------------------


class TestEventDayMapper:
    def test_to_domain(self) -> None:
        phase_model = EventDayPhaseModel(
            id=A_UUID,
            event_day_id=B_UUID,
            operational_phase_id=C_UUID,
            start_min=480,
            end_min=720,
        )
        model = EventDayModel(
            id=B_UUID,
            event_date=date(2026, 7, 10),
            operational_profile_id=C_UUID,
            attendance_level_id=uuid4(),
            operational_start_min=480,
            operational_end_min=1380,
        )
        model.phases = [phase_model]

        entity = event_day_to_domain(model)
        assert entity.id == B_UUID
        assert entity.event_date == date(2026, 7, 10)
        assert entity.operational_profile_id == C_UUID
        assert entity.operational_start_min == 480
        assert entity.operational_end_min == 1380
        assert len(entity.phases) == 1
        assert entity.phases[0].id == A_UUID
        assert entity.phases[0].event_day_id == B_UUID
        assert entity.phases[0].operational_phase_id == C_UUID
        assert entity.phases[0].start_min == 480
        assert entity.phases[0].end_min == 720
        assert isinstance(entity, EventDay)

    def test_to_model(self) -> None:
        att_id = uuid4()
        phase = EventDayPhase(
            id=A_UUID,
            event_day_id=B_UUID,
            operational_phase_id=C_UUID,
            start_min=480,
            end_min=720,
        )
        entity = EventDay(
            id=B_UUID,
            event_date=date(2026, 7, 10),
            operational_profile_id=C_UUID,
            attendance_level_id=att_id,
            operational_start_min=480,
            operational_end_min=1380,
            phases=(phase,),
        )

        model = event_day_to_model(entity)
        assert model.id == B_UUID
        assert model.event_date == date(2026, 7, 10)
        assert model.operational_profile_id == C_UUID
        assert model.attendance_level_id == att_id
        assert model.operational_start_min == 480
        assert model.operational_end_min == 1380
        assert len(model.phases) == 1
        assert model.phases[0].id == A_UUID
        assert model.phases[0].event_day_id == B_UUID
        assert model.phases[0].operational_phase_id == C_UUID
        assert model.phases[0].start_min == 480
        assert model.phases[0].end_min == 720
        assert isinstance(model, EventDayModel)

    def test_round_trip_preserves_all_data(self) -> None:
        att_id = uuid4()
        phase = EventDayPhase(
            id=A_UUID,
            event_day_id=B_UUID,
            operational_phase_id=C_UUID,
            start_min=480,
            end_min=720,
        )
        original = EventDay(
            id=B_UUID,
            event_date=date(2026, 7, 10),
            operational_profile_id=C_UUID,
            attendance_level_id=att_id,
            operational_start_min=480,
            operational_end_min=1380,
            phases=(phase,),
        )

        model = event_day_to_model(original)
        result = event_day_to_domain(model)

        assert result.id == original.id
        assert result.event_date == original.event_date
        assert result.operational_profile_id == original.operational_profile_id
        assert result.attendance_level_id == original.attendance_level_id
        assert result.operational_start_min == original.operational_start_min
        assert result.operational_end_min == original.operational_end_min
        assert len(result.phases) == len(original.phases)
        for rp, op in zip(result.phases, original.phases):
            assert rp.id == op.id
            assert rp.event_day_id == op.event_day_id
            assert rp.operational_phase_id == op.operational_phase_id
            assert rp.start_min == op.start_min
            assert rp.end_min == op.end_min

    def test_to_model_sets_fk_on_phases(self) -> None:
        day_id = uuid4()
        phase = EventDayPhase(
            id=uuid4(),
            event_day_id=uuid4(),
            operational_phase_id=uuid4(),
            start_min=0,
            end_min=100,
        )
        entity = EventDay(
            id=day_id,
            event_date=date(2026, 7, 10),
            operational_profile_id=uuid4(),
            attendance_level_id=uuid4(),
            operational_start_min=0,
            operational_end_min=100,
            phases=(phase,),
        )

        model = event_day_to_model(entity)
        for p in model.phases:
            assert p.event_day_id == day_id

    def test_multiple_phases(self) -> None:
        att_id = uuid4()
        phases = (
            EventDayPhase(id=uuid4(), event_day_id=B_UUID, operational_phase_id=uuid4(), start_min=0, end_min=500),
            EventDayPhase(id=uuid4(), event_day_id=B_UUID, operational_phase_id=uuid4(), start_min=500, end_min=1000),
        )
        entity = EventDay(
            id=B_UUID,
            event_date=date(2026, 7, 10),
            operational_profile_id=uuid4(),
            attendance_level_id=att_id,
            operational_start_min=0,
            operational_end_min=1000,
            phases=phases,
        )

        model = event_day_to_model(entity)
        result = event_day_to_domain(model)

        assert len(result.phases) == 2
        assert result.phases[0].start_min == 0
        assert result.phases[0].end_min == 500
        assert result.phases[1].start_min == 500
        assert result.phases[1].end_min == 1000

    def test_boundary_values(self) -> None:
        att_id = uuid4()
        phase = EventDayPhase(
            id=uuid4(),
            event_day_id=B_UUID,
            operational_phase_id=uuid4(),
            start_min=0,
            end_min=1440,
        )
        entity = EventDay(
            id=B_UUID,
            event_date=date(2026, 7, 10),
            operational_profile_id=uuid4(),
            attendance_level_id=att_id,
            operational_start_min=0,
            operational_end_min=1440,
            phases=(phase,),
        )

        model = event_day_to_model(entity)
        result = event_day_to_domain(model)
        assert result.operational_start_min == 0
        assert result.operational_end_min == 1440
        assert result.phases[0].start_min == 0
        assert result.phases[0].end_min == 1440
