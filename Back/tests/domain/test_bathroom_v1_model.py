"""Tests de Bathroom V1: flujo por fase, Ley de Little y distribución espacial."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest

from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone import Zone
from src.domain.models.bathroom_v1_model import (
    DEFAULT_ALPHA,
    BathroomV1Model,
)
from src.domain.models.specialized_model import (
    ModelExecutionContext,
    ModelSpecificResult,
)

SCENARIO_A_INTENSITIES = (0.20, 0.35, 0.50, 0.65, 0.85, 1.00, 0.90, 0.70, 0.40, 0.15)
TEST_USE_RATE_PER_PERSON_HOUR = 0.1


def make_zone(
    id_value: str,
    capacity: int,
    distance: float | None,
    type: str = "servicios",
    subtipo: str = "banos",
    available_capacity: int | None = None,
) -> Zone:
    return Zone(
        id=UUID(id_value),
        name=f"Banos {id_value}",
        zone_type_id=UUID("10000000-0000-0000-0000-000000000001"),
        capacity=capacity,
        type=type,
        subtipo=subtipo,
        reference_point_distance=distance,
        available_capacity=available_capacity,
    )


def make_phase(start: int, end: int, intensity: float, sequence: int) -> EventDayPhase:
    return EventDayPhase(
        id=UUID(f"20000000-0000-0000-0000-{sequence:012d}"),
        event_day_id=UUID("30000000-0000-0000-0000-000000000001"),
        operational_phase_id=UUID(f"10000000-0000-0000-0000-{sequence:012d}"),
        start_min=start,
        end_min=end,
        intensity=intensity,
    )


def make_ten_phases(intensities: tuple[float, ...]) -> list[EventDayPhase]:
    return [
        make_phase(start=i * 60, end=(i + 1) * 60, intensity=intensity, sequence=i + 1)
        for i, intensity in enumerate(intensities)
    ]


def make_attendance(max_people: int | None = 8000) -> AttendanceLevel:
    return AttendanceLevel(
        name="Alta",
        min_people=5000,
        max_people=max_people,
        id="55555555-0000-0000-0000-000000000001",
    )


def make_context(
    zone: Zone,
    intensity: float = 0.25,
    start: int = 0,
    end: int = 60,
    max_people: int = 8000,
    duration_min: int = 240,
) -> ModelExecutionContext:
    phase = make_phase(start, end, intensity, sequence=1)
    op_phase = OperationalPhase(
        id=UUID("10000000-0000-0000-0000-000000000001"),
        name="Peak",
        sequence_order=1,
    )
    return ModelExecutionContext(
        timestamp=datetime(2026, 7, 15, 15, 0),
        zone=zone,
        active_operational_phase=op_phase,
        active_event_day_phase=phase,
        intensity=intensity,
        attendance_level=make_attendance(max_people),
        event_impact=0,
        density_factor=None,
        active_restriction=None,
        reference_point_distance=zone.reference_point_distance,
        estimated_vehicles=None,
        average_parking_duration=None,
        average_duration_min=duration_min,
    )


def make_model(
    alpha: float = DEFAULT_ALPHA,
    use_rate_per_person_hour: float = TEST_USE_RATE_PER_PERSON_HOUR,
) -> BathroomV1Model:
    return BathroomV1Model(
        alpha=alpha,
        use_rate_per_person_hour=use_rate_per_person_hour,
    )


class TestContrato:
    def test_model_id(self) -> None:
        assert BathroomV1Model().model_id == "bathroom_v1"

    def test_alpha_default(self) -> None:
        assert BathroomV1Model().alpha == DEFAULT_ALPHA

    def test_supports_servicios_banos(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        assert BathroomV1Model().supports(zone) is True

    def test_supports_rejects_servicios_sin_subtipo(self) -> None:
        zone = make_zone(
            "a0000000-0000-0000-0000-000000000001",
            500,
            100.0,
            type="servicios",
            subtipo="hidratacion",
        )
        assert BathroomV1Model().supports(zone) is False

    def test_supports_rejects_other_types(self) -> None:
        zona_comida = make_zone(
            "a0000000-0000-0000-0000-000000000002",
            500,
            100.0,
            type="comida",
            subtipo=None,
        )
        assert BathroomV1Model().supports(zona_comida) is False

    def test_execute_returns_model_specific_result(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        result = make_model().execute(make_context(zone))
        assert isinstance(result, ModelSpecificResult)
        assert result.model_id == "bathroom_v1"
        assert result.zone_id == zone.id

    def test_execute_single_zone_phase_1(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 2000, 100.0)
        result = make_model().execute(
            make_context(zone, intensity=0.25, start=0, end=60)
        )
        data = result.data
        assert data["bathroom_id"] == str(zone.id)
        assert data["occupied"] == pytest.approx(800.0)
        assert data["capacity"] == 2000
        assert data["occupancy_ratio"] == pytest.approx(0.4)
        assert data["free_ratio"] == pytest.approx(0.6)
        assert data["free_spaces"] == pytest.approx(1200.0)
        assert data["distance"] == pytest.approx(100.0)
        assert data["unabsorbed"] == pytest.approx(0.0)

    def test_execute_does_not_invent_extra_outputs(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        data = make_model().execute(make_context(zone)).data
        forbidden = {
            "availability",
            "availability_level",
            "availability_rank",
            "probability",
            "rank",
            "recommendation",
            "operational_state",
            "confidence",
            "estimated_wait",
            "saturation_level",
        }
        assert forbidden.isdisjoint(data.keys())

    def test_execute_rejects_non_bathroom_zone(self) -> None:
        zone = make_zone(
            "a0000000-0000-0000-0000-000000000002",
            500,
            100.0,
            type="comida",
            subtipo=None,
        )
        with pytest.raises(ValueError):
            BathroomV1Model().execute(make_context(zone))

    def test_execute_rejects_max_people_null(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        with pytest.raises(ValueError):
            BathroomV1Model().execute(make_context(zone, max_people=None))

    def test_execute_rejects_missing_duration(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        context = make_context(zone)
        without_duration = ModelExecutionContext(
            timestamp=context.timestamp,
            zone=context.zone,
            active_operational_phase=context.active_operational_phase,
            active_event_day_phase=context.active_event_day_phase,
            intensity=context.intensity,
            attendance_level=context.attendance_level,
            event_impact=0,
            density_factor=None,
            active_restriction=None,
            reference_point_distance=context.reference_point_distance,
            estimated_vehicles=None,
            average_parking_duration=None,
            average_duration_min=None,
        )
        with pytest.raises(ValueError):
            BathroomV1Model().execute(without_duration)


class TestFormulaFlujoContinuo:
    def test_people_present_is_max_people_times_intensity(self) -> None:
        model = BathroomV1Model()
        assert model.people_present(8000, 0.25) == pytest.approx(2000.0)
        assert model.people_present(8000, 0.5) == pytest.approx(4000.0)
        assert model.people_present(8000, 1.25) == pytest.approx(10000.0)

    def test_arrival_rate_is_people_present_times_configured_u(self) -> None:
        model = make_model(use_rate_per_person_hour=0.1)
        people_present = model.people_present(5000, 0.8)
        assert model.arrival_rate_per_hour(people_present) == pytest.approx(400.0)

    def test_littles_law_occupancy_with_real_scenario(self) -> None:
        model = make_model(use_rate_per_person_hour=0.1)
        people_present = model.people_present(5000, 0.8)
        arrival_rate = model.arrival_rate_per_hour(people_present)
        duration_hours = model.duration_hours(5)
        assert model.concurrent_occupancy(arrival_rate, duration_hours) == pytest.approx(
            33.3333333333
        )

    def test_occupancy_scales_with_intensity_use_rate_and_duration(self) -> None:
        base = make_model(use_rate_per_person_hour=0.1)
        n = base.people_present(5000, 0.5)
        base_l = base.concurrent_occupancy(base.arrival_rate_per_hour(n), 5 / 60)

        higher_intensity = base.people_present(5000, 1.0)
        intensity_l = base.concurrent_occupancy(
            base.arrival_rate_per_hour(higher_intensity), 5 / 60
        )
        higher_u = make_model(use_rate_per_person_hour=0.2)
        use_rate_l = higher_u.concurrent_occupancy(
            higher_u.arrival_rate_per_hour(n), 5 / 60
        )
        longer_use = base.concurrent_occupancy(
            base.arrival_rate_per_hour(n), 10 / 60
        )

        assert intensity_l == pytest.approx(2 * base_l)
        assert use_rate_l == pytest.approx(2 * base_l)
        assert longer_use == pytest.approx(2 * base_l)

    def test_zero_use_rate_produces_zero_occupancy(self) -> None:
        model = make_model(use_rate_per_person_hour=0.0)
        rate = model.arrival_rate_per_hour(model.people_present(5000, 1.0))
        assert model.concurrent_occupancy(rate, 5 / 60) == 0.0

    def test_duration_hours_conversion(self) -> None:
        model = BathroomV1Model()
        assert model.duration_hours(60) == pytest.approx(1.0)
        assert model.duration_hours(240) == pytest.approx(4.0)
        assert model.duration_hours(5) == pytest.approx(5 / 60.0)

    def test_phase_duration_does_not_change_simultaneous_occupancy(self) -> None:
        model = make_model()
        one_hour = model.temporal_step(100.0, 1.0, 5 / 60)
        two_hours = model.temporal_step(100.0, 2.0, 5 / 60)
        assert one_hour.stock == pytest.approx(two_hours.stock)
        assert two_hours.v_expected == pytest.approx(2 * one_hour.v_expected)

    def test_simulation_does_not_carry_occupancy_between_phases(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 10000, 100.0)
        phases = make_ten_phases((1.0, 0.1))
        model = make_model()
        results = model.simulate(phases, [zone], 8000, 5 / 60)
        expected_second_phase = model.distribute(
            {}, [zone], results[1].stock
        )
        assert dict(results[1].occupied) == pytest.approx(expected_second_phase)
        assert results[1].remain == 0.0
        assert results[1].exits == 0.0
        assert results[1].unabsorbed == 0.0


class TestDistribucionEspacial:
    def _zones_abc(self) -> list[Zone]:
        return [
            make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0),
            make_zone("a0000000-0000-0000-0000-000000000002", 1000, 400.0),
            make_zone("a0000000-0000-0000-0000-000000000003", 2000, 900.0),
        ]

    def test_ejemplo_31_7(self) -> None:
        zones = self._zones_abc()
        prev = {
            zones[0].id: 300.0,
            zones[1].id: 500.0,
            zones[2].id: 700.0,
        }
        occupied = BathroomV1Model().distribute(prev, zones, 2000.0)
        assert occupied[zones[0].id] == pytest.approx(500.0, abs=0.1)
        assert occupied[zones[1].id] == pytest.approx(672.7, abs=0.1)
        assert occupied[zones[2].id] == pytest.approx(827.3, abs=0.1)
        assert sum(occupied.values()) == pytest.approx(2000.0, abs=0.1)

    def test_contraccion_libera_menos_preferida_primero(self) -> None:
        zones = self._zones_abc()
        prev = {
            zones[0].id: 500.0,
            zones[1].id: 672.7,
            zones[2].id: 827.3,
        }
        occupied = BathroomV1Model().distribute(prev, zones, 1800.0)
        assert occupied[zones[0].id] == pytest.approx(500.0, abs=0.1)
        assert occupied[zones[1].id] == pytest.approx(672.7, abs=0.1)
        assert occupied[zones[2].id] == pytest.approx(627.3, abs=0.1)
        assert sum(occupied.values()) == pytest.approx(1800.0, abs=0.1)

    def test_alpha_cero_sin_efecto_de_distancia(self) -> None:
        zones = self._zones_abc()
        occupied = BathroomV1Model(alpha=0.0).distribute({}, zones, 1500.0)
        assert sum(occupied.values()) == pytest.approx(1500.0, abs=0.1)
        assert occupied[zones[0].id] == pytest.approx(500.0, abs=0.1)
        assert occupied[zones[1].id] == pytest.approx(500.0, abs=0.1)
        assert occupied[zones[2].id] == pytest.approx(500.0, abs=0.1)

    def test_distribute_independiente_del_orden(self) -> None:
        zones = self._zones_abc()
        prev = {
            zones[0].id: 300.0,
            zones[1].id: 500.0,
            zones[2].id: 700.0,
        }
        direct = BathroomV1Model().distribute(prev, zones, 2000.0)
        reversed_zones = list(reversed(zones))
        flipped = BathroomV1Model().distribute(prev, reversed_zones, 2000.0)
        for zone in zones:
            assert flipped[zone.id] == pytest.approx(direct[zone.id], abs=1e-9)


class TestInvariantes:
    def test_estado_inicial_cero(self) -> None:
        zones = self._zones_abc()
        initial = BathroomV1Model().initial_occupied(zones)
        assert sum(initial.values()) == pytest.approx(0.0)

    def test_occupied_acotado_por_capacidad(self) -> None:
        zones = self._zones_abc()
        capacities = {zone.id: zone.capacity for zone in zones}
        total_capacity = sum(capacities.values())
        results = make_model().simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )
        for phase in results:
            occupied_sum = sum(phase.occupied.values())
            assert occupied_sum == pytest.approx(
                min(phase.stock, total_capacity), abs=1e-6
            )
            assert phase.unabsorbed == pytest.approx(0.0)
            for zone_id, occupied in phase.occupied.items():
                assert 0.0 <= occupied <= capacities[zone_id]

    def _zones_abc(self) -> list[Zone]:
        return [
            make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0),
            make_zone("a0000000-0000-0000-0000-000000000002", 1000, 400.0),
            make_zone("a0000000-0000-0000-0000-000000000003", 2000, 900.0),
        ]


class TestDeterminismo:
    def test_execute_determinista(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        model = make_model()
        context = make_context(zone)
        first = model.execute(context).data
        for _ in range(5):
            assert model.execute(context).data == first

    def test_simulate_determinista(self) -> None:
        zones = [
            make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0),
            make_zone("a0000000-0000-0000-0000-000000000002", 1000, 400.0),
            make_zone("a0000000-0000-0000-0000-000000000003", 2000, 900.0),
        ]
        model = make_model()
        first = model.simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )
        second = model.simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )
        for a, b in zip(first, second):
            assert a == b


class TestBathroomFlowGradient:
    """La saturación varía con la población, u y permanencia según Little."""

    MAX_PEOPLE = 40000
    D5_MIN_HOURS = 5 / 60.0
    ZONE_CAPACITY = 50
    PHASE_MINUTES = 60

    def _zones(self) -> list[Zone]:
        return [
            make_zone(
                f"a0000000-0000-0000-0000-00000000000{i}",
                self.ZONE_CAPACITY,
                100.0,
            )
            for i in range(1, 5)
        ]

    def _phase(self, intensity: float):
        model = make_model()
        phases = [make_phase(0, self.PHASE_MINUTES, intensity, sequence=1)]
        return model, model.simulate(
            phases, self._zones(), self.MAX_PEOPLE, self.D5_MIN_HOURS
        )[0]

    def _saturations(self, model: BathroomV1Model, phase) -> list[float]:
        return [
            model.indices(occupied, self.ZONE_CAPACITY)[0]
            for occupied in phase.occupied.values()
        ]

    def test_saturation_scales_proportionally_below_capacity(self) -> None:
        low_model, low = self._phase(0.3)
        high_model, high = self._phase(0.45)
        assert low.stock == pytest.approx(100.0)
        assert high.stock == pytest.approx(150.0)
        assert self._saturations(high_model, high)[0] == pytest.approx(
            1.5 * self._saturations(low_model, low)[0]
        )

    def test_zone_capacities_still_bound_occupancy(self) -> None:
        model, phase = self._phase(0.6)
        assert phase.stock == pytest.approx(200.0)
        assert sum(phase.occupied.values()) == pytest.approx(200.0)
        assert all(
            occupied <= self.ZONE_CAPACITY
            for occupied in phase.occupied.values()
        )
        assert all(s == pytest.approx(1.0) for s in self._saturations(model, phase))

    def test_intensity_monotonicity(self) -> None:
        saturations = []
        for intensity in (0.01, 0.1, 0.3, 0.45):
            model, phase = self._phase(intensity)
            saturations.append(max(self._saturations(model, phase)))
        assert all(a <= b for a, b in zip(saturations, saturations[1:]))

    def test_parking_v1_unchanged(self) -> None:
        from src.domain.models.parking_v1_model import ParkingV1Model

        parking_zone = Zone(
            id=UUID("a0000000-0000-0000-0000-000000000001"),
            name="Parking A",
            zone_type_id=UUID("10000000-0000-0000-0000-000000000001"),
            capacity=10000,
            type="estacionamiento",
            subtipo=None,
            reference_point_distance=100.0,
        )
        results = ParkingV1Model().simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), [parking_zone], 8000, 4.0
        )
        assert results[1].stock == pytest.approx(4046.08, abs=0.1)


class TestInputsInvalidos:
    def test_people_present_sin_max_people(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().people_present(None, 0.25)

    def test_people_present_max_people_negativo(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().people_present(-1, 0.25)

    def test_people_present_sin_intensity(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().people_present(8000, None)

    def test_people_present_intensity_negativa(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().people_present(8000, -0.1)

    def test_people_present_tipo_invalido(self) -> None:
        with pytest.raises(TypeError):
            BathroomV1Model().people_present("8000", 0.25)

    def test_missing_use_rate_is_not_defaulted(self) -> None:
        model = BathroomV1Model()
        with pytest.raises(ValueError, match="bathroom_use_rate_per_person_hour"):
            model.arrival_rate_per_hour(100.0)

    def test_use_rate_negative_rejected(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model(use_rate_per_person_hour=-0.1)

    def test_use_rate_non_finite_rejected(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model(use_rate_per_person_hour=float("nan"))

    def test_duration_hours_none(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().duration_hours(None)

    def test_duration_hours_cero(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().duration_hours(0)

    def test_duration_hours_negativo(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().duration_hours(-5)

    def test_duration_hours_bool(self) -> None:
        with pytest.raises(TypeError):
            BathroomV1Model().duration_hours(True)

    def test_concurrent_occupancy_rejects_negative_rate(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().concurrent_occupancy(-1.0, 4.0)

    def test_temporal_step_rejects_nonpositive_phase_duration(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().temporal_step(100.0, 0.0, 4.0)

    def test_distribute_stock_negativo(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        with pytest.raises(ValueError):
            BathroomV1Model().distribute({}, [zone], -1.0)

    def test_distribute_sin_zonas(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().distribute({}, [], 100.0)

    def test_distribute_alpha_negativo(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        with pytest.raises(ValueError):
            BathroomV1Model().distribute({}, [zone], 100.0, alpha=-0.1)

    def test_indices_occupied_negativo(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().indices(-1.0, 500)

    def test_indices_capacidad_cero(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().indices(0.0, 0)

    def test_constructor_alpha_negativo(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model(alpha=-0.001)

    def test_constructor_alpha_bool(self) -> None:
        with pytest.raises(TypeError):
            BathroomV1Model(alpha=True)

    def test_simulate_sin_fases(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        with pytest.raises(ValueError):
            make_model().simulate([], [zone], 8000, 4.0)

    def test_simulate_sin_zonas(self) -> None:
        with pytest.raises(ValueError):
            make_model().simulate(
                make_ten_phases(SCENARIO_A_INTENSITIES), [], 8000, 4.0
            )

    def test_simulate_max_people_none(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        with pytest.raises(ValueError):
            make_model().simulate(
                make_ten_phases(SCENARIO_A_INTENSITIES), [zone], None, 4.0
            )