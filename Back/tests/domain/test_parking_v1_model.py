"""Tests del modelo especializado Parking V1 (RFC-008).

Cubre la matemática cerrada de `MODELO_PROBABILISTICO_PARKING_V1.md`:
fórmulas principales, límites de capacidad, permanencia/stock,
distribución espacial, demanda > capacidad, invariantes V1-V12,
determinismo, inputs inválidos y contrato `SpecializedModel`.
"""
from __future__ import annotations

import math
from datetime import datetime
from uuid import UUID

import pytest

from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone import Zone
from src.domain.models.parking_v1_model import (
    DEFAULT_ALPHA,
    ParkingV1Model,
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
    type: str = "estacionamiento",
) -> Zone:
    return Zone(
        id=UUID(id_value),
        name=f"Parking {id_value}",
        zone_type_id=UUID("10000000-0000-0000-0000-000000000001"),
        capacity=capacity,
        type=type,
        reference_point_distance=distance,
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


def make_context(
    zone: Zone,
    intensity: float = 0.25,
    start: int = 0,
    end: int = 60,
    estimated_vehicles: int = 8000,
    duration: float = 4.0,
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
        attendance_level=None,
        event_impact=0,
        density_factor=None,
        active_restriction=None,
        reference_point_distance=zone.reference_point_distance,
        estimated_vehicles=estimated_vehicles,
        average_parking_duration=duration,
    )


class TestContrato:
    def test_model_id(self) -> None:
        assert ParkingV1Model().model_id == "parking_v1"

    def test_alpha_default(self) -> None:
        assert ParkingV1Model().alpha == DEFAULT_ALPHA

    def test_supports_estacionamiento(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        assert ParkingV1Model().supports(zone) is True

    def test_supports_rejects_other_types(self) -> None:
        zona_comida = make_zone(
            "a0000000-0000-0000-0000-000000000002",
            500,
            100.0,
            type="comida",
        )
        assert ParkingV1Model().supports(zona_comida) is False

    def test_execute_returns_model_specific_result(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        result = ParkingV1Model().execute(make_context(zone))
        assert isinstance(result, ModelSpecificResult)
        assert result.model_id == "parking_v1"
        assert result.zone_id == zone.id

    def test_execute_single_zone_phase_1(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        result = ParkingV1Model().execute(
            make_context(zone, intensity=0.25, start=0, end=60)
        )
        data = result.data
        assert data["parking_id"] == str(zone.id)
        assert data["occupied"] == pytest.approx(500.0)
        assert data["capacity"] == 500
        assert data["occupancy_ratio"] == pytest.approx(1.0)
        assert data["free_ratio"] == pytest.approx(0.0)
        assert data["free_spaces"] == pytest.approx(0.0)
        assert data["distance"] == pytest.approx(100.0)
        assert data["unabsorbed"] == pytest.approx(1500.0)

    def test_execute_does_not_invent_extra_outputs(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        data = ParkingV1Model().execute(make_context(zone)).data
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

    def test_execute_rejects_non_parking_zone(self) -> None:
        zone = make_zone(
            "a0000000-0000-0000-0000-000000000002",
            500,
            100.0,
            type="comida",
        )
        with pytest.raises(ValueError):
            ParkingV1Model().execute(make_context(zone))


class TestFormulasPrincipales:
    def test_v_expected(self) -> None:
        model = ParkingV1Model()
        assert model.v_expected(8000, 0.25) == pytest.approx(2000.0)
        assert model.v_expected(8000, 0.50) == pytest.approx(4000.0)
        assert model.v_expected(8000, 1.00) == pytest.approx(8000.0)
        assert model.v_expected(8000, 0.0) == pytest.approx(0.0)

    def test_v_expected_intensity_above_one(self) -> None:
        assert ParkingV1Model().v_expected(8000, 1.25) == pytest.approx(10000.0)

    def test_retention(self) -> None:
        model = ParkingV1Model()
        assert model.retention(1.0, 4.0) == pytest.approx(math.exp(-1 / 4), abs=1e-9)
        assert model.retention(2.0, 4.0) == pytest.approx(math.exp(-2 / 4), abs=1e-9)

    def test_retention_zero_delta(self) -> None:
        assert ParkingV1Model().retention(0.0, 4.0) == pytest.approx(1.0)

    def test_temporal_step_first_phase(self) -> None:
        result = ParkingV1Model().temporal_step(0.0, 1600.0, 10000.0, 1.0, 4.0)
        assert result.remain == pytest.approx(0.0)
        assert result.exits == pytest.approx(0.0)
        assert result.entries == pytest.approx(1600.0)
        assert result.stock == pytest.approx(1600.0)
        assert result.unabsorbed == pytest.approx(0.0)

    def test_temporal_step_scenario_a_phase_2(self) -> None:
        result = ParkingV1Model().temporal_step(1600.0, 2800.0, 10000.0, 1.0, 4.0)
        assert result.remain == pytest.approx(1246.08, abs=0.1)
        assert result.exits == pytest.approx(353.92, abs=0.1)
        assert result.entries == pytest.approx(1553.92, abs=0.1)
        assert result.stock == pytest.approx(2800.0, abs=0.1)

    def test_temporal_step_descenso_sin_vaciado_inmediato(self) -> None:
        result = ParkingV1Model().temporal_step(5000.0, 2000.0, 10000.0, 1.0, 4.0)
        assert result.remain == pytest.approx(3894.0, abs=0.1)
        assert result.entries == pytest.approx(0.0)
        assert result.stock == pytest.approx(3894.0, abs=0.1)
        assert result.unabsorbed == pytest.approx(0.0)


class TestLimitesDeCapacidad:
    def test_stock_nunca_supera_capacidad_total(self) -> None:
        model = ParkingV1Model()
        for expected in (4000.0, 5200.0, 6800.0, 8000.0):
            result = model.temporal_step(2180.64, expected, 3500.0, 1.0, 4.0)
            assert result.stock <= 3500.0
            assert result.stock == pytest.approx(3500.0, abs=0.1)

    def test_entrada_efectiva_acotada_por_capacidad(self) -> None:
        result = ParkingV1Model().temporal_step(2800.0, 4000.0, 3500.0, 1.0, 4.0)
        assert result.remain == pytest.approx(2180.64, abs=0.1)
        assert result.entries == pytest.approx(1319.36, abs=0.1)
        assert result.stock == pytest.approx(3500.0, abs=0.1)
        assert result.unabsorbed == pytest.approx(500.0, abs=0.1)


class TestPermanenciaStock:
    def test_simulate_escenario_a_seccion_30(self) -> None:
        zones = [make_zone("a0000000-0000-0000-0000-000000000001", 10000, 100.0)]
        results = ParkingV1Model().simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )
        assert len(results) == 10
        table = {
            1: (1600.0, 0.0, 0.0, 1600.0, 1600.0, 0.0),
            2: (2800.0, 1246.08, 353.92, 1553.92, 2800.0, 0.0),
            3: (4000.0, 2180.64, 619.36, 1819.36, 4000.0, 0.0),
            4: (5200.0, 3115.20, 884.80, 2084.80, 5200.0, 0.0),
            7: (7200.0, 6230.40, 1769.60, 969.60, 7200.0, 0.0),
            8: (5600.0, 5607.36, 1592.64, 0.0, 5607.36, 0.0),
            10: (1200.0, 3401.05, 965.97, 0.0, 3401.05, 0.0),
        }
        for index, (v, remain, exits, entries, stock, unabsorbed) in table.items():
            phase = results[index - 1]
            assert phase.index == index
            assert phase.v_expected == pytest.approx(v, abs=0.1)
            assert phase.remain == pytest.approx(remain, abs=0.1)
            assert phase.exits == pytest.approx(exits, abs=0.1)
            assert phase.entries == pytest.approx(entries, abs=0.1)
            assert phase.stock == pytest.approx(stock, abs=0.1)
            assert phase.unabsorbed == pytest.approx(unabsorbed, abs=0.1)

    def test_rotacion_sum_entradas_mayor_que_v_max(self) -> None:
        zones = [make_zone("a0000000-0000-0000-0000-000000000001", 10000, 100.0)]
        results = ParkingV1Model().simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )
        total_entries = sum(phase.entries for phase in results)
        assert total_entries > 8000.0

    def test_simulate_pico_central(self) -> None:
        zones = [make_zone("a0000000-0000-0000-0000-000000000001", 10000, 100.0)]
        results = ParkingV1Model().simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )
        assert results[5].stock == pytest.approx(8000.0, abs=0.1)


class TestDistribucionEspacial:
    def _parkings_abc(self) -> list[Zone]:
        return [
            make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0),
            make_zone("a0000000-0000-0000-0000-000000000002", 1000, 400.0),
            make_zone("a0000000-0000-0000-0000-000000000003", 2000, 900.0),
        ]

    def test_ejemplo_31_7(self) -> None:
        zones = self._parkings_abc()
        prev = {
            zones[0].id: 300.0,
            zones[1].id: 500.0,
            zones[2].id: 700.0,
        }
        occupied = ParkingV1Model().distribute(prev, zones, 2000.0)
        assert occupied[zones[0].id] == pytest.approx(500.0, abs=0.1)
        assert occupied[zones[1].id] == pytest.approx(672.7, abs=0.1)
        assert occupied[zones[2].id] == pytest.approx(827.3, abs=0.1)
        assert sum(occupied.values()) == pytest.approx(2000.0, abs=0.1)

    def test_ejemplo_31_8_ocupacion_previa_nula(self) -> None:
        zones = self._parkings_abc()
        occupied = ParkingV1Model().distribute({}, zones, 1300.0)
        assert occupied[zones[0].id] == pytest.approx(500.0, abs=0.5)
        assert occupied[zones[1].id] == pytest.approx(460.6, abs=0.5)
        assert occupied[zones[2].id] == pytest.approx(339.4, abs=0.5)
        assert sum(occupied.values()) == pytest.approx(1300.0, abs=0.3)

    def test_ejemplo_31_9_proximidad_llena_antes(self) -> None:
        zones = [
            make_zone("a0000000-0000-0000-0000-000000000001", 1000, 100.0),
            make_zone("a0000000-0000-0000-0000-000000000002", 2000, 500.0),
            make_zone("a0000000-0000-0000-0000-000000000003", 4000, 1500.0),
        ]
        occupied = ParkingV1Model().distribute({}, zones, 3500.0)
        assert occupied[zones[0].id] == pytest.approx(1000.0, abs=0.3)
        assert occupied[zones[1].id] == pytest.approx(1562.2, abs=0.3)
        assert occupied[zones[2].id] == pytest.approx(937.8, abs=0.3)
        assert sum(occupied.values()) == pytest.approx(3500.0, abs=0.3)

    def test_reparto_ponderado_sin_tope(self) -> None:
        zones = [
            make_zone("a0000000-0000-0000-0000-000000000001", 1000, 100.0),
            make_zone("a0000000-0000-0000-0000-000000000002", 2000, 500.0),
            make_zone("a0000000-0000-0000-0000-000000000003", 4000, 1500.0),
        ]
        occupied = ParkingV1Model().distribute({}, zones, 500.0)
        assert occupied[zones[0].id] == pytest.approx(230.0, abs=0.3)
        assert occupied[zones[1].id] == pytest.approx(168.7, abs=0.3)
        assert occupied[zones[2].id] == pytest.approx(101.2, abs=0.3)
        assert sum(occupied.values()) == pytest.approx(500.0, abs=0.3)

    def test_contraccion_libera_menos_preferida_primero(self) -> None:
        zones = self._parkings_abc()
        prev = {
            zones[0].id: 500.0,
            zones[1].id: 672.7,
            zones[2].id: 827.3,
        }
        occupied = ParkingV1Model().distribute(prev, zones, 1800.0)
        assert occupied[zones[0].id] == pytest.approx(500.0, abs=0.1)
        assert occupied[zones[1].id] == pytest.approx(672.7, abs=0.1)
        assert occupied[zones[2].id] == pytest.approx(627.3, abs=0.1)
        assert sum(occupied.values()) == pytest.approx(1800.0, abs=0.1)

    def test_alpha_cero_sin_efecto_de_distancia(self) -> None:
        zones = self._parkings_abc()
        occupied = ParkingV1Model(alpha=0.0).distribute({}, zones, 1500.0)
        assert sum(occupied.values()) == pytest.approx(1500.0, abs=0.1)
        assert occupied[zones[0].id] == pytest.approx(500.0, abs=0.1)
        assert occupied[zones[1].id] == pytest.approx(500.0, abs=0.1)
        assert occupied[zones[2].id] == pytest.approx(500.0, abs=0.1)

    def test_distribute_independiente_del_orden(self) -> None:
        zones = self._parkings_abc()
        prev = {
            zones[0].id: 300.0,
            zones[1].id: 500.0,
            zones[2].id: 700.0,
        }
        direct = ParkingV1Model().distribute(prev, zones, 2000.0)
        reversed_zones = list(reversed(zones))
        flipped = ParkingV1Model().distribute(prev, reversed_zones, 2000.0)
        for zone in zones:
            assert flipped[zone.id] == pytest.approx(direct[zone.id], abs=1e-9)


class TestDemandaMayorCapacidad:
    def _zones_escenario_b(self) -> list[Zone]:
        return [
            make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0),
            make_zone("a0000000-0000-0000-0000-000000000002", 1000, 400.0),
            make_zone("a0000000-0000-0000-0000-000000000003", 2000, 900.0),
        ]

    def test_simulate_escenario_b_seccion_30(self) -> None:
        zones = self._zones_escenario_b()
        results = ParkingV1Model().simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )
        table = {
            1: (1600.0, 0.0),
            3: (3500.0, 500.0),
            6: (3500.0, 4500.0),
            7: (3500.0, 3700.0),
            8: (3500.0, 2100.0),
            9: (3200.0, 0.0),
            10: (2492.16, 0.0),
        }
        for index, (stock, unabsorbed) in table.items():
            phase = results[index - 1]
            assert phase.stock == pytest.approx(stock, abs=0.1)
            assert phase.unabsorbed == pytest.approx(unabsorbed, abs=0.1)

    def test_unabsorbed_es_demanda_no_stock(self) -> None:
        zones = self._zones_escenario_b()
        phase_6 = ParkingV1Model().simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )[5]
        assert phase_6.unabsorbed == pytest.approx(4500.0, abs=0.1)
        assert phase_6.stock == pytest.approx(3500.0, abs=0.1)
        assert sum(phase_6.occupied.values()) == pytest.approx(3500.0, abs=0.1)


class TestInvariantes:
    def _simulate_escenario_b(self) -> list:
        zones = [
            make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0),
            make_zone("a0000000-0000-0000-0000-000000000002", 1000, 400.0),
            make_zone("a0000000-0000-0000-0000-000000000003", 2000, 900.0),
        ]
        return zones, ParkingV1Model().simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )

    def test_v1_v_expected_puede_superar_capacidad(self) -> None:
        _, results = self._simulate_escenario_b()
        assert any(
            phase.v_expected > 3500.0 for phase in results
        )
        assert results[5].v_expected == pytest.approx(8000.0)

    def test_v2_o_t_nunca_supera_capacidad_total(self) -> None:
        _, results = self._simulate_escenario_b()
        assert all(phase.stock <= 3500.0 + 1e-9 for phase in results)

    def test_v3_nunca_occupied_sobre_capacidad(self) -> None:
        zones, results = self._simulate_escenario_b()
        capacity_by_id = {zone.id: zone.capacity for zone in zones}
        for phase in results:
            for zone_id, occupied in phase.occupied.items():
                assert occupied <= capacity_by_id[zone_id] + 1e-9

    def test_v4_suma_occupied_igual_o_t(self) -> None:
        _, results = self._simulate_escenario_b()
        for phase in results:
            assert sum(phase.occupied.values()) == pytest.approx(
                phase.stock, abs=1e-6
            )

    def test_v5_unabsorbed_igual_max_cero_v_expected_menos_o_t(self) -> None:
        _, results = self._simulate_escenario_b()
        for phase in results:
            expected = max(0.0, phase.v_expected - phase.stock)
            assert phase.unabsorbed == pytest.approx(expected, abs=1e-6)

    def test_v6_v7_distancia_y_capacidad_no_alteran_v_expected(self) -> None:
        zones = [
            make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0),
            make_zone("a0000000-0000-0000-0000-000000000002", 1000, 400.0),
            make_zone("a0000000-0000-0000-0000-000000000003", 2000, 900.0),
        ]
        model = ParkingV1Model()
        phases = make_ten_phases(SCENARIO_A_INTENSITIES)
        base = model.simulate(phases, zones, 8000, 4.0)
        other_zones = [
            make_zone("b0000000-0000-0000-0000-000000000001", 1500, 50.0),
            make_zone("b0000000-0000-0000-0000-000000000002", 2500, 800.0),
        ]
        variant = model.simulate(phases, other_zones, 8000, 4.0)
        for a, b in zip(base, variant):
            assert a.v_expected == pytest.approx(b.v_expected, abs=1e-9)

    def test_v8_permanencia_sin_doble_conteo_entre_fases(self) -> None:
        _, results = self._simulate_escenario_b()
        r = math.exp(-1 / 4)
        for previous, current in zip(results, results[1:]):
            assert current.remain == pytest.approx(previous.stock * r, abs=1e-6)
            assert current.stock == pytest.approx(
                current.remain + current.entries, abs=1e-6
            )

    def test_v9_cada_vehiculo_en_una_unica_zona(self) -> None:
        _, results = self._simulate_escenario_b()
        for phase in results:
            assert len(phase.occupied) == 3
            assert sum(phase.occupied.values()) == pytest.approx(
                phase.stock, abs=1e-6
            )

    def test_v10_stock_distinto_de_flujo(self) -> None:
        _, results = self._simulate_escenario_b()
        assert results[1].stock == pytest.approx(2800.0, abs=0.1)
        assert results[1].entries == pytest.approx(1553.92, abs=0.1)
        assert results[1].stock != pytest.approx(results[1].entries, abs=1.0)
        assert results[7].stock == pytest.approx(3500.0, abs=0.1)
        assert results[7].v_expected == pytest.approx(5600.0, abs=0.1)
        assert results[7].stock != pytest.approx(results[7].v_expected, abs=1.0)

    def test_v11_unabsorbed_no_se_contabiliza_como_estacionado(self) -> None:
        _, results = self._simulate_escenario_b()
        phase_6 = results[5]
        assert phase_6.unabsorbed == pytest.approx(4500.0, abs=0.1)
        assert sum(phase_6.occupied.values()) == pytest.approx(
            phase_6.stock, abs=1e-6
        )
        assert phase_6.stock < phase_6.v_expected

    def test_v12_suma_de_v_expected_no_son_vehiculos_distintos(self) -> None:
        _, results = self._simulate_escenario_b()
        total_expected = sum(phase.v_expected for phase in results)
        assert total_expected > 8000.0
        assert all(phase.stock <= 3500.0 + 1e-9 for phase in results)


class TestDeterminismo:
    def test_execute_determinista(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        model = ParkingV1Model()
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
        model = ParkingV1Model()
        first = model.simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )
        second = model.simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES), zones, 8000, 4.0
        )
        for a, b in zip(first, second):
            assert a == b


class TestInputsInvalidos:
    def test_v_expected_sin_estimated_vehicles(self) -> None:
        with pytest.raises(ValueError):
            ParkingV1Model().v_expected(None, 0.25)

    def test_v_expected_estimated_vehicles_negativo(self) -> None:
        with pytest.raises(ValueError):
            ParkingV1Model().v_expected(-1, 0.25)

    def test_v_expected_sin_intensity(self) -> None:
        with pytest.raises(ValueError):
            ParkingV1Model().v_expected(8000, None)

    def test_v_expected_intensity_negativa(self) -> None:
        with pytest.raises(ValueError):
            ParkingV1Model().v_expected(8000, -0.1)

    def test_v_expected_tipo_invalido(self) -> None:
        with pytest.raises(TypeError):
            ParkingV1Model().v_expected("8000", 0.25)

    def test_retention_delta_negativo(self) -> None:
        with pytest.raises(ValueError):
            ParkingV1Model().retention(-1.0, 4.0)

    def test_retention_duration_cero(self) -> None:
        with pytest.raises(ValueError):
            ParkingV1Model().retention(1.0, 0.0)

    def test_retention_duration_none(self) -> None:
        with pytest.raises(TypeError):
            ParkingV1Model().retention(1.0, None)

    def test_temporal_step_prev_stock_negativo(self) -> None:
        with pytest.raises(ValueError):
            ParkingV1Model().temporal_step(-1.0, 1000.0, 3500.0, 1.0, 4.0)

    def test_temporal_step_capacidad_cero(self) -> None:
        with pytest.raises(ValueError):
            ParkingV1Model().temporal_step(0.0, 1000.0, 0.0, 1.0, 4.0)

    def test_distribute_stock_negativo(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        with pytest.raises(ValueError):
            ParkingV1Model().distribute({}, [zone], -1.0)

    def test_distribute_sin_zonas(self) -> None:
        with pytest.raises(ValueError):
            ParkingV1Model().distribute({}, [], 100.0)

    def test_distribute_alpha_negativo(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        with pytest.raises(ValueError):
            ParkingV1Model().distribute({}, [zone], 100.0, alpha=-0.1)

    def test_indices_occupied_negativo(self) -> None:
        with pytest.raises(ValueError):
            ParkingV1Model().indices(-1.0, 500)

    def test_indices_capacidad_cero(self) -> None:
        with pytest.raises(ValueError):
            ParkingV1Model().indices(0.0, 0)

    def test_constructor_alpha_negativo(self) -> None:
        with pytest.raises(ValueError):
            ParkingV1Model(alpha=-0.001)

    def test_constructor_alpha_bool(self) -> None:
        with pytest.raises(TypeError):
            ParkingV1Model(alpha=True)

    def test_simulate_sin_fases(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        with pytest.raises(ValueError):
            ParkingV1Model().simulate([], [zone], 8000, 4.0)

    def test_simulate_sin_zonas(self) -> None:
        with pytest.raises(ValueError):
            ParkingV1Model().simulate(
                make_ten_phases(SCENARIO_A_INTENSITIES), [], 8000, 4.0
            )

    def test_execute_sin_estimated_vehicles(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        context = make_context(zone)
        context_without = ModelExecutionContext(
            timestamp=context.timestamp,
            zone=context.zone,
            active_operational_phase=context.active_operational_phase,
            active_event_day_phase=context.active_event_day_phase,
            intensity=context.intensity,
            attendance_level=None,
            event_impact=0,
            density_factor=None,
            active_restriction=None,
            reference_point_distance=context.reference_point_distance,
            estimated_vehicles=None,
            average_parking_duration=4.0,
        )
        with pytest.raises(ValueError):
            ParkingV1Model().execute(context_without)