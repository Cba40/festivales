"""Tests de la infraestructura de modelos especializados (Corrección 7).

Cubre: selección determinista, selección por contrato, entrega de Intensity
como contexto (sin fórmula universal), resultado específico del modelo,
incorporación a la salida territorial y no-generación universal de campos.
"""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

import pytest

from src.application.context_engine.context_engine import ContextEngine
from src.application.context_engine.model_selector import ModelSelector
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction, ZoneBehavior
from src.domain.models.specialized_model import (
    ModelExecutionContext,
    ModelSpecificResult,
)


class FakeParkingModel:
    """Modelo de prueba (sin matemática real) para el dominio estacionamiento."""

    model_id = "fake_parking_model"

    def __init__(self, result_data: dict | None = None) -> None:
        self._result_data = result_data or {}
        self.last_context: ModelExecutionContext | None = None

    def supports(self, zone: Zone) -> bool:
        return zone.type == "estacionamiento"

    def execute(self, context: ModelExecutionContext) -> ModelSpecificResult:
        self.last_context = context
        return ModelSpecificResult(
            model_id=self.model_id,
            zone_id=context.zone.id,
            data=dict(self._result_data),
        )


class FakeGastronomyModel:
    """Segundo modelo de prueba para comprobar la selección determinista."""

    model_id = "fake_gastronomy_model"

    def supports(self, zone: Zone) -> bool:
        return zone.type == "comida"

    def execute(self, context: ModelExecutionContext) -> ModelSpecificResult:
        return ModelSpecificResult(
            model_id=self.model_id,
            zone_id=context.zone.id,
            data={"category": "gastronomia"},
        )


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
def event_day_phase(peak_phase: OperationalPhase) -> EventDayPhase:
    return EventDayPhase(
        id=UUID("20000000-0000-0000-0000-000000000001"),
        event_day_id=UUID("30000000-0000-0000-0000-000000000001"),
        operational_phase_id=peak_phase.id,
        start_min=840,
        end_min=1080,
        intensity=0.5,
    )


@pytest.fixture
def event_day(event_day_phase: EventDayPhase) -> EventDay:
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
def operational_phases(peak_phase: OperationalPhase) -> dict[UUID, OperationalPhase]:
    return {peak_phase.id: peak_phase}


@pytest.fixture
def zones() -> list[Zone]:
    return [
        Zone(
            id=UUID("a0000000-0000-0000-0000-000000000001"),
            name="Parking Norte",
            zone_type_id=UUID("10000000-0000-0000-0000-000000000001"),
            capacity=500,
            type="estacionamiento",
            reference_point_distance=1250.75,
        ),
        Zone(
            id=UUID("a0000000-0000-0000-0000-000000000002"),
            name="Sector Gastronomico",
            zone_type_id=UUID("10000000-0000-0000-0000-000000000002"),
            capacity=2000,
            type="comida",
        ),
    ]


@pytest.fixture
def zone_behaviors(
    peak_phase: OperationalPhase,
) -> dict[tuple[UUID, UUID], ZoneBehavior]:
    return {
        (
            UUID("10000000-0000-0000-0000-000000000001"),
            peak_phase.id,
        ): ZoneBehavior(
            zone_type_id=UUID("10000000-0000-0000-0000-000000000001"),
            operational_phase_id=peak_phase.id,
            density_factor=0.8,
            flow_restriction=FlowRestriction.OPEN,
        ),
        (
            UUID("10000000-0000-0000-0000-000000000002"),
            peak_phase.id,
        ): ZoneBehavior(
            zone_type_id=UUID("10000000-0000-0000-0000-000000000002"),
            operational_phase_id=peak_phase.id,
            density_factor=0.6,
            flow_restriction=FlowRestriction.OPEN,
        ),
    }


@pytest.fixture
def attendance() -> AttendanceLevel:
    return AttendanceLevel(
        name="Normal",
        min_people=10000,
        max_people=25000,
    )


def _predict(engine: ContextEngine, *, timestamp, zones, zone_behaviors, operational_phases, attendance, event_day):
    return engine.predict(
        timestamp=timestamp,
        zones=zones,
        zone_behaviors=zone_behaviors,
        operational_phases=operational_phases,
        attendance_level=attendance,
        event_day=event_day,
        events=[],
    )


class TestDeterministicSelection:
    def test_same_zone_always_selects_same_model(self, zones: list[Zone]) -> None:
        selector = ModelSelector()
        selector.register(FakeParkingModel())
        selector.register(FakeGastronomyModel())

        parking = zones[0]
        first = selector.select(parking)
        second = selector.select(parking)

        assert first is not None
        assert first is second
        assert first.model_id == "fake_parking_model"


class TestSelectionThroughContract:
    def test_context_engine_selects_model_via_selector(
        self,
        timestamp,
        zones,
        zone_behaviors,
        operational_phases,
        attendance,
        event_day,
    ) -> None:
        selector = ModelSelector()
        selector.register(FakeParkingModel(result_data={"free_spaces": 12}))
        engine = ContextEngine(model_selector=selector)

        result = _predict(
            engine,
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            operational_phases=operational_phases,
            attendance=attendance,
            event_day=event_day,
        )

        parking_state = next(
            s for s in result.zone_states if s.zone_id == zones[0].id
        )
        gastronomy_state = next(
            s for s in result.zone_states if s.zone_id == zones[1].id
        )

        assert parking_state.model_result == {"free_spaces": 12}
        assert parking_state.model_result is not None
        assert gastronomy_state.model_result is None


class TestIntensityDelivery:
    def test_context_engine_delivers_intensity_without_universal_formula(
        self,
        timestamp,
        zones,
        zone_behaviors,
        operational_phases,
        attendance,
        event_day,
        event_day_phase,
    ) -> None:
        capturing = FakeParkingModel()
        selector = ModelSelector()
        selector.register(capturing)
        engine = ContextEngine(model_selector=selector)

        result = _predict(
            engine,
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            operational_phases=operational_phases,
            attendance=attendance,
            event_day=event_day,
        )

        assert capturing.last_context is not None
        assert capturing.last_context.intensity == event_day_phase.intensity
        assert capturing.last_context.zone.id == zones[0].id

        parking_state = next(
            s for s in result.zone_states if s.zone_id == zones[0].id
        )
        assert parking_state.saturation_level is None


class TestSpecificResult:
    def test_specialized_model_returns_specific_result(
        self,
        zones: list[Zone],
        peak_phase: OperationalPhase,
        event_day_phase: EventDayPhase,
    ) -> None:
        model = FakeParkingModel(result_data={"free_spaces": 7})
        selector = ModelSelector()
        selector.register(model)
        engine = ContextEngine(model_selector=selector)

        zone = zones[0]
        context = ModelExecutionContext(
            timestamp=datetime(2026, 7, 15, 15, 0),
            zone=zone,
            active_operational_phase=peak_phase,
            active_event_day_phase=event_day_phase,
            intensity=0.5,
            attendance_level=None,
            event_impact=0,
            density_factor=0.8,
            active_restriction=FlowRestriction.OPEN,
            reference_point_distance=zone.reference_point_distance,
        )

        result = model.execute(context)

        assert result.model_id == "fake_parking_model"
        assert result.zone_id == zone.id
        assert result.data == {"free_spaces": 7}


class TestIncorporationIntoPrediction:
    def test_context_engine_incorporates_specific_result(
        self,
        timestamp,
        zones,
        zone_behaviors,
        operational_phases,
        attendance,
        event_day,
    ) -> None:
        selector = ModelSelector()
        selector.register(
            FakeParkingModel(
                result_data={
                    "free_spaces": 7,
                    "saturation_level": 0.4,
                    "operational_state": "OPEN",
                }
            )
        )
        engine = ContextEngine(model_selector=selector)

        result = _predict(
            engine,
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            operational_phases=operational_phases,
            attendance=attendance,
            event_day=event_day,
        )

        parking_state = next(
            s for s in result.zone_states if s.zone_id == zones[0].id
        )
        assert parking_state.model_result == {
            "free_spaces": 7,
            "saturation_level": 0.4,
            "operational_state": "OPEN",
        }
        assert parking_state.saturation_level == 0.4
        assert parking_state.operational_state == "OPEN"


class TestNoUniversalFields:
    def test_context_engine_does_not_generate_universal_state_fields(
        self,
        timestamp,
        zones,
        zone_behaviors,
        operational_phases,
        attendance,
        event_day,
    ) -> None:
        selector = ModelSelector()
        selector.register(FakeParkingModel(result_data={"free_spaces": 12}))
        engine = ContextEngine(model_selector=selector)

        result = _predict(
            engine,
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            operational_phases=operational_phases,
            attendance=attendance,
            event_day=event_day,
        )

        parking_state = next(
            s for s in result.zone_states if s.zone_id == zones[0].id
        )
        assert parking_state.availability is None
        assert parking_state.saturation_level is None
        assert parking_state.estimated_wait is None
        assert parking_state.confidence is None
        assert parking_state.model_result == {"free_spaces": 12}