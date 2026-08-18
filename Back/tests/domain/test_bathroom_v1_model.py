"""Tests del modelo especializado Baños V1 (replica de Parking V1, RFC-008).

Cubre la matemática cerrada de `SERVICIOS_PERSONAS_DISENO.md §7`: la misma
estructura temporal/espacial de Parking V1 con dos inputs distintos
(AttendanceLevel.max_people y ServiceConfig.average_duration_min en minutos,
convertida a horas). Verifica la NOTA TERMINOLÓGICA: con permanencias cortas
(minutos) y fases de horas, `exp(-Δt/D) ≈ 0` entre fases; el stock de una fase
prácticamente no se conserva hacia la siguiente (NO es "flujo instantáneo").
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
        assert data["unabsorbed"] == pytest.approx(1500.0)

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
        assert result.stock == pytest.approx(1600.0)
        assert result.unabsorbed == pytest.approx(0.0)

    def test_temporal_step_scenario_a_phase_2(self) -> None:
        result = BathroomV1Model().temporal_step(1600.0, 2800.0, 10000.0, 1.0, 4.0)
        assert result.remain == pytest.approx(1246.08, abs=0.1)
        assert result.exits == pytest.approx(353.92, abs=0.1)
        assert result.entries == pytest.approx(2800.0, abs=0.1)
        assert result.stock == pytest.approx(4046.08, abs=0.1)
        assert result.unabsorbed == pytest.approx(0.0)


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
        # Primera fase acumula stock real.
        assert results[0].stock == pytest.approx(1600.0)
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

    def test_stock_no_se_clava_en_v_expected_con_d_corto(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 10000, 100.0)
        phases = make_ten_phases(SCENARIO_A_INTENSITIES)
        results = BathroomV1Model().simulate(phases, [zone], 8000, self.D5_MIN_HOURS)
        # Cada fase "arranca de cero" salvo un resto despreciable (< 0.1):
        # stock ≈ entries ≈ v_expected.
        for phase in results:
            assert phase.stock == pytest.approx(phase.entries, abs=0.1)
            assert phase.entries == pytest.approx(
                min(phase.v_expected, 10000.0), abs=1e-3
            )


class TestLimitesDeCapacidad:
    def test_stock_nunca_supera_capacidad_total(self) -> None:
        model = BathroomV1Model()
        for expected in (4000.0, 5200.0, 6800.0, 8000.0):
            result = model.temporal_step(2180.64, expected, 3500.0, 1.0, 4.0)
            assert result.stock <= 3500.0
            assert result.stock == pytest.approx(3500.0, abs=0.1)

    def test_entrada_efectiva_acotada_por_capacidad(self) -> None:
        result = BathroomV1Model().temporal_step(2800.0, 4000.0, 3500.0, 1.0, 4.0)
        assert result.remain == pytest.approx(2180.64, abs=0.1)
        assert result.entries == pytest.approx(1319.36, abs=0.1)
        assert result.stock == pytest.approx(3500.0, abs=0.1)
        assert result.unabsorbed == pytest.approx(2680.64, abs=0.1)


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
        results = BathroomV1Model().simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )
        for phase in results:
            assert sum(phase.occupied.values()) == pytest.approx(
                phase.stock, abs=1e-6
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