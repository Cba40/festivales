"""Tests del modelo especializado Baños V1 (modelo de FLUJO, Little's law).

Cubre la matemática cerrada de `SERVICIOS_PERSONAS_DISENO.md §7` adaptada a
servicios de ALTA ROTACIÓN: `v_expected = max_people × intensity`,
`concurrent_occupancy = v_expected × (D_hours / Δt_hours)`, `stock` =
ocupación concurrente (no acumula entre fases), `unabsorbed` = demanda que
excede la capacidad de servicio de la fase (`capacity × Δt / D`) y NO
incrementa stock. A diferencia de Parking V1 (stock concurrente), la
saturación es un gradiente, no un colapso binario.
"""
from __future__ import annotations

import math
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
        result = BathroomV1Model().execute(make_context(zone))
        assert isinstance(result, ModelSpecificResult)
        assert result.model_id == "bathroom_v1"
        assert result.zone_id == zone.id

    def test_execute_single_zone_phase_1(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        result = BathroomV1Model().execute(
            make_context(zone, intensity=0.25, start=0, end=60)
        )
        data = result.data
        assert data["bathroom_id"] == str(zone.id)
        assert data["occupied"] == pytest.approx(500.0)
        assert data["capacity"] == 500
        assert data["occupancy_ratio"] == pytest.approx(1.0)
        assert data["free_ratio"] == pytest.approx(0.0)
        assert data["free_spaces"] == pytest.approx(0.0)
        assert data["distance"] == pytest.approx(100.0)
        assert data["unabsorbed"] == pytest.approx(1875.0)

    def test_execute_does_not_invent_extra_outputs(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        data = BathroomV1Model().execute(make_context(zone)).data
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


class TestFormulasPrincipales:
    def test_v_expected(self) -> None:
        model = BathroomV1Model()
        assert model.v_expected(8000, 0.25) == pytest.approx(2000.0)
        assert model.v_expected(8000, 0.50) == pytest.approx(4000.0)
        assert model.v_expected(8000, 1.00) == pytest.approx(8000.0)
        assert model.v_expected(8000, 0.0) == pytest.approx(0.0)

    def test_v_expected_intensity_above_one(self) -> None:
        assert BathroomV1Model().v_expected(8000, 1.25) == pytest.approx(10000.0)

    def test_duration_hours_conversion(self) -> None:
        model = BathroomV1Model()
        assert model.duration_hours(60) == pytest.approx(1.0)
        assert model.duration_hours(240) == pytest.approx(4.0)
        assert model.duration_hours(5) == pytest.approx(5 / 60.0)

    def test_retention(self) -> None:
        model = BathroomV1Model()
        assert model.retention(1.0, 4.0) == pytest.approx(math.exp(-1 / 4), abs=1e-9)
        assert model.retention(2.0, 4.0) == pytest.approx(math.exp(-2 / 4), abs=1e-9)

    def test_retention_zero_delta(self) -> None:
        assert BathroomV1Model().retention(0.0, 4.0) == pytest.approx(1.0)

    def test_temporal_step_first_phase(self) -> None:
        result = BathroomV1Model().temporal_step(0.0, 1600.0, 10000.0, 1.0, 4.0)
        assert result.remain == pytest.approx(0.0)
        assert result.exits == pytest.approx(0.0)
        assert result.entries == pytest.approx(1600.0)
        assert result.stock == pytest.approx(1600.0 * 4.0)
        assert result.unabsorbed == pytest.approx(0.0)

    def test_temporal_step_scenario_a_phase_2(self) -> None:
        result = BathroomV1Model().temporal_step(1600.0, 2800.0, 10000.0, 1.0, 4.0)
        assert result.remain == pytest.approx(1246.08, abs=0.1)
        assert result.exits == pytest.approx(353.92, abs=0.1)
        # Capacidad de servicio de la fase = 10000 × (1/4) = 2500.
        assert result.entries == pytest.approx(2500.0, abs=0.1)
        assert result.stock == pytest.approx(2800.0 * 4.0, abs=0.1)
        assert result.unabsorbed == pytest.approx(300.0, abs=0.1)


class TestPermanenciaCorta:
    """D corto (minutos) con fases de horas: `r_t = exp(-Δt/D) ≈ 0` entre fases.

    NOTA TERMINOLÓGICA: esto NO es "flujo instantáneo"; significa que el stock
    de una fase prácticamente no se conserva hacia la siguiente. El servicio en
    sí conserva su permanencia real (minutos) por uso.
    """

    D5_MIN_HOURS = 5 / 60.0

    def test_retention_5min_en_fase_de_1h(self) -> None:
        r = BathroomV1Model().retention(1.0, self.D5_MIN_HOURS)
        assert r == pytest.approx(math.exp(-60 / 5), abs=1e-9)
        assert r == pytest.approx(0.0, abs=1e-4)

    def test_stock_no_se_conserva_entre_fases(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 10000, 100.0)
        phases = make_ten_phases(SCENARIO_A_INTENSITIES)
        results = BathroomV1Model().simulate(
            phases, [zone], 8000, self.D5_MIN_HOURS
        )
        # Primera fase: ocupación concurrente (Little) = v × D/Δt.
        assert results[0].stock == pytest.approx(1600.0 * (5 / 60.0))
        # Hacia la siguiente fase el stock prácticamente no se conserva: la
        # fracción retenida es exp(-12) ≈ 6e-6, despreciable frente al stock.
        for first, second in zip(results, results[1:]):
            assert second.remain == pytest.approx(
                first.stock * math.exp(-60 / 5), rel=1e-9
            )
            assert second.remain < second.stock * 1e-3

    def test_servicio_no_instantaneo_por_uso(self) -> None:
        # La permanencia por uso sigue siendo real (5 minutos): se refleja en
        # que la retención con fases cortas (Δt pequeño) se acerca a 1.0.
        r_1min = BathroomV1Model().retention(5 / 60.0, self.D5_MIN_HOURS)
        assert r_1min == pytest.approx(math.exp(-1.0), abs=1e-9)
        assert 0.3 < r_1min < 0.5

    def test_stock_concurrente_little_vs_v_expected(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 10000, 100.0)
        phases = make_ten_phases(SCENARIO_A_INTENSITIES)
        results = BathroomV1Model().simulate(phases, [zone], 8000, self.D5_MIN_HOURS)
        # Alta rotación: la ocupación concurrente es v × (D/Δt) = v/12, una
        # fracción de las llegadas, NO se clava en v_expected.
        for phase in results:
            assert phase.stock == pytest.approx(
                phase.v_expected * self.D5_MIN_HOURS, abs=1e-6
            )
            # Capacidad de servicio = 10000 × (1 / (5/60)) = 120000 ≫ v: todo
            # se absorbe.
            assert phase.entries == pytest.approx(phase.v_expected, abs=1e-3)
            assert phase.unabsorbed == pytest.approx(0.0)


class TestLimitesDeCapacidad:
    def test_stock_concurrente_puede_superar_capacidad(self) -> None:
        model = BathroomV1Model()
        for expected in (4000.0, 5200.0, 6800.0, 8000.0):
            result = model.temporal_step(2180.64, expected, 3500.0, 1.0, 4.0)
            # stock = ocupación concurrente (Little's law): puede exceder la
            # capacidad física; la capacidad se aplica en distribute().
            assert result.stock == pytest.approx(expected * 4.0)

    def test_entrada_acotada_por_capacidad_de_servicio(self) -> None:
        result = BathroomV1Model().temporal_step(2800.0, 4000.0, 3500.0, 1.0, 4.0)
        assert result.remain == pytest.approx(2180.64, abs=0.1)
        assert result.exits == pytest.approx(619.36, abs=0.1)
        # Capacidad de servicio de la fase = 3500 × (1/4) = 875.
        assert result.entries == pytest.approx(875.0, abs=0.1)
        assert result.stock == pytest.approx(4000.0 * 4.0, abs=0.1)
        assert result.unabsorbed == pytest.approx(4000.0 - 875.0, abs=0.1)


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
        results = BathroomV1Model().simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )
        for phase in results:
            occupied_sum = sum(phase.occupied.values())
            # El stock (ocupación concurrente) puede superar la capacidad;
            # la ocupación física se acota en distribute() a la capacidad total.
            assert occupied_sum == pytest.approx(
                min(phase.stock, total_capacity), abs=1e-6
            )
            assert phase.unabsorbed == pytest.approx(
                max(0.0, phase.v_expected - phase.entries), abs=1e-6
            )
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
        model = BathroomV1Model()
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
        model = BathroomV1Model()
        first = model.simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )
        second = model.simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )
        for a, b in zip(first, second):
            assert a == b


class TestBathroomFlowGradient:
    """Modelo de FLUJO (Little's law): gradiente de saturación por intensidad.

    Escenario de producción: max_people=40000, D=5 min, 4 zonas × 50 = 200 de
    capacidad, fases de 60 min. Con stock concurrente cualquier v_expected ≥
    200 colapsaba (modo binario); con flujo la saturación es un gradiente.
    """

    MAX_PEOPLE = 40000
    D5_MIN_HOURS = 5 / 60.0
    ZONE_CAPACITY = 50
    PHASE_MINUTES = 60
    ROTATIONS = 60 / 5  # Δt / D = 12 usos por sitio en la fase

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
        model = BathroomV1Model()
        phases = [make_phase(0, self.PHASE_MINUTES, intensity, sequence=1)]
        return model, model.simulate(
            phases, self._zones(), self.MAX_PEOPLE, self.D5_MIN_HOURS
        )[0]

    def _saturations(self, model: BathroomV1Model, phase) -> list[float]:
        return [
            model.indices(occupied, self.ZONE_CAPACITY)[0]
            for occupied in phase.occupied.values()
        ]

    def test_gradient_low_intensity_no_collapse(self) -> None:
        model, phase = self._phase(0.005)
        assert phase.v_expected == pytest.approx(200.0)
        # concurrent_occupancy = 200 × (5/60) / 1 = 16.67
        assert phase.stock == pytest.approx(200.0 * self.D5_MIN_HOURS)
        # saturation ≈ (16.67/4) / 50 = 0.083 → NO colapsado
        saturations = self._saturations(model, phase)
        assert all(s < 0.75 for s in saturations)
        assert saturations[0] == pytest.approx(
            200.0 * self.D5_MIN_HOURS / 4 / self.ZONE_CAPACITY
        )
        # capacidad de servicio = 200 × 12 = 2400 ≥ 200 → nada no atendido
        assert phase.unabsorbed == pytest.approx(0.0)

    def test_gradient_threshold_intensity(self) -> None:
        model, phase = self._phase(0.045)
        assert phase.v_expected == pytest.approx(1800.0)
        # concurrent_occupancy = 1800 × (5/60) = 150
        assert phase.stock == pytest.approx(1800.0 * self.D5_MIN_HOURS)
        # saturation = (150/4) / 50 = 0.75 → umbral de colapso
        saturations = self._saturations(model, phase)
        assert saturations[0] == pytest.approx(0.75)
        # capacidad de servicio = 200 × 12 = 2400 ≥ 1800 → nada no atendido
        assert phase.unabsorbed == pytest.approx(0.0)

    def test_gradient_pre_collapse(self) -> None:
        model, phase = self._phase(0.03)
        assert phase.v_expected == pytest.approx(1200.0)
        # concurrent_occupancy = 1200 × (5/60) = 100 → saturación ≈ 0.50
        assert phase.stock == pytest.approx(1200.0 * self.D5_MIN_HOURS)
        saturations = self._saturations(model, phase)
        assert all(s < 0.75 for s in saturations)
        assert saturations[0] == pytest.approx(0.50)
        assert phase.unabsorbed == pytest.approx(0.0)

    def test_gradient_collapse_threshold(self) -> None:
        # El umbral de "colapsado" es saturation_level >= 0.75: 0.045 lo
        # cruza (saturación física = capacidad total), 0.03 no.
        _, collapse = self._phase(0.045)
        _, pre_collapse = self._phase(0.03)
        # 0.045 → 0.7499999999999999 (arte de coma flotante); cruza el umbral
        assert all(
            s + 1e-9 >= 0.75
            for s in self._saturations(BathroomV1Model(), collapse)
        )
        assert all(
            s < 0.75
            for s in self._saturations(BathroomV1Model(), pre_collapse)
        )

    def test_gradient_high_intensity_collapse(self) -> None:
        model, phase = self._phase(0.1)
        assert phase.v_expected == pytest.approx(4000.0)
        # concurrent_occupancy = 4000 × (5/60) = 333.33 > capacidad física 200
        assert phase.stock == pytest.approx(4000.0 * self.D5_MIN_HOURS)
        # la ocupación física se acota en distribute() a la capacidad total
        assert sum(phase.occupied.values()) == pytest.approx(200.0)
        saturations = self._saturations(model, phase)
        assert all(s == pytest.approx(1.0) for s in saturations)
        # demanda no atendida: 4000 - 200×12 = 1600
        assert phase.unabsorbed == pytest.approx(1600.0)

    def test_unabsorbed_does_not_increment_stock(self) -> None:
        _, phase = self._phase(0.1)
        concurrent = 4000.0 * self.D5_MIN_HOURS
        # stock == concurrent_occupancy (NO stock + unabsorbed)
        assert phase.stock == pytest.approx(concurrent)
        assert phase.stock != pytest.approx(concurrent + phase.unabsorbed)
        occupied_sum = sum(phase.occupied.values())
        assert occupied_sum == pytest.approx(min(concurrent, 200.0), abs=1e-6)
        assert occupied_sum != pytest.approx(concurrent + phase.unabsorbed)

    def test_monotonicity_gradient(self) -> None:
        saturations: list[float] = []
        unabsorbed: list[float] = []
        for intensity in (0.001, 0.01, 0.03, 0.06, 0.1, 0.2):
            model, phase = self._phase(intensity)
            saturations.append(max(self._saturations(model, phase)))
            unabsorbed.append(phase.unabsorbed)
        assert all(a <= b for a, b in zip(saturations, saturations[1:]))
        assert all(a <= b for a, b in zip(unabsorbed, unabsorbed[1:]))

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
    def test_v_expected_sin_max_people(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().v_expected(None, 0.25)

    def test_v_expected_max_people_negativo(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().v_expected(-1, 0.25)

    def test_v_expected_sin_intensity(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().v_expected(8000, None)

    def test_v_expected_intensity_negativa(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().v_expected(8000, -0.1)

    def test_v_expected_tipo_invalido(self) -> None:
        with pytest.raises(TypeError):
            BathroomV1Model().v_expected("8000", 0.25)

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

    def test_retention_delta_negativo(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().retention(-1.0, 4.0)

    def test_retention_duration_cero(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().retention(1.0, 0.0)

    def test_retention_duration_none(self) -> None:
        with pytest.raises(TypeError):
            BathroomV1Model().retention(1.0, None)

    def test_temporal_step_prev_stock_negativo(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().temporal_step(-1.0, 1000.0, 3500.0, 1.0, 4.0)

    def test_temporal_step_capacidad_cero(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().temporal_step(0.0, 1000.0, 0.0, 1.0, 4.0)

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
            BathroomV1Model().simulate([], [zone], 8000, 4.0)

    def test_simulate_sin_zonas(self) -> None:
        with pytest.raises(ValueError):
            BathroomV1Model().simulate(
                make_ten_phases(SCENARIO_A_INTENSITIES), [], 8000, 4.0
            )

    def test_simulate_max_people_none(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        with pytest.raises(ValueError):
            BathroomV1Model().simulate(
                make_ten_phases(SCENARIO_A_INTENSITIES), [zone], None, 4.0
            )