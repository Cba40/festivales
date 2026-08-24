"""Tests del modelo especializado Food V1 (stock acumulado, exponencial).

Cubre la matemática cerrada de `MODELO PROBABILÍSTICO FOOD V1.md` (PARTE II,
validaciones V1-V12): `P_expected = max_people × intensity` (llegadas por
fase), capacidad de servicio con permanencias INDIVIDUALES
(`Σ [capacity_i × Δt / D_i]`), permanencia efectiva armónica ponderada por
capacidad (`D_eff`), ecuación temporal exponencial
(`O_t = remain + contribution`), distribución espacial iterativa y residual
instantáneo `unabsorbed_t` (NO backlog). A diferencia de Baños V1 (flujo,
Little's law), Food V1 ACUMULA stock entre fases con retención
`r_t = exp(-Δt/D_eff)`.
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
from src.domain.models.food_v1_model import (
    DEFAULT_ALPHA,
    FoodV1Model,
)
from src.domain.models.specialized_model import (
    ModelExecutionContext,
    ModelSpecificResult,
)

SCENARIO_A_INTENSITIES = (0.20, 0.35, 0.50, 0.65, 0.85, 1.00, 0.90, 0.70, 0.40, 0.15)

# Ejemplo normativo del documento (§24): caps 50/200/100, D 20/30/60 min,
# distancias 100/400/900 m, max_people=10000, intensity=0.30, Δt=60 min.
DOC_CAPACITIES = (50, 200, 100)
DOC_DURATIONS_MIN = (20, 30, 60)
DOC_DISTANCES = (100.0, 400.0, 900.0)
DOC_MAX_PEOPLE = 10_000
DOC_INTENSITY = 0.30
DOC_DELTA_HOURS = 1.0
DOC_TOTAL_CAPACITY = 350.0
DOC_SERVICE_CAPACITY = 650.0
DOC_D_EFFECTIVE_HOURS = 350.0 / 650.0


def make_zone(
    id_value: str,
    capacity: int,
    distance: float | None,
    type: str = "comida",
    subtipo: str | None = "patio_de_comidas",
) -> Zone:
    return Zone(
        id=UUID(id_value),
        name=f"Comida {id_value}",
        zone_type_id=UUID("b0000000-0000-0000-0000-000000000002"),
        capacity=capacity,
        type=type,
        subtipo=subtipo,
        reference_point_distance=distance,
    )


def make_doc_zones() -> list[Zone]:
    subtipos = ("foodtruck", "patio_de_comidas", "restaurante")
    return [
        make_zone(
            f"a0000000-0000-0000-0000-{i + 1:012d}",
            DOC_CAPACITIES[i],
            DOC_DISTANCES[i],
            subtipo=subtipos[i],
        )
        for i in range(3)
    ]


def doc_durations_hours(zones: list[Zone]) -> dict[UUID, float]:
    return {
        zone.id: minutes / 60.0
        for zone, minutes in zip(zones, DOC_DURATIONS_MIN)
    }


def make_phase(start: int, end: int, intensity: float | None, sequence: int) -> EventDayPhase:
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
    duration_min: int = 30,
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
        assert FoodV1Model().model_id == "food_v1"

    def test_alpha_default(self) -> None:
        assert FoodV1Model().alpha == DEFAULT_ALPHA

    def test_supports_comida_con_subtipo(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        assert FoodV1Model().supports(zone) is True

    def test_supports_comida_sin_subtipo(self) -> None:
        zone = make_zone(
            "a0000000-0000-0000-0000-000000000001", 500, 100.0, subtipo=None
        )
        assert FoodV1Model().supports(zone) is True

    def test_supports_rejects_estacionamiento(self) -> None:
        zone = make_zone(
            "a0000000-0000-0000-0000-000000000002",
            500,
            100.0,
            type="estacionamiento",
            subtipo=None,
        )
        assert FoodV1Model().supports(zone) is False

    def test_supports_rejects_servicios_banos(self) -> None:
        zone = make_zone(
            "a0000000-0000-0000-0000-000000000002",
            500,
            100.0,
            type="servicios",
            subtipo="banos",
        )
        assert FoodV1Model().supports(zone) is False

    def test_supports_rejects_otro_slug(self) -> None:
        zone = make_zone(
            "a0000000-0000-0000-0000-000000000002",
            500,
            100.0,
            type="puesto_comida",
            subtipo=None,
        )
        assert FoodV1Model().supports(zone) is False

    def test_execute_returns_model_specific_result(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        result = FoodV1Model().execute(make_context(zone))
        assert isinstance(result, ModelSpecificResult)
        assert result.model_id == "food_v1"
        assert result.zone_id == zone.id

    def test_execute_single_zone_fase_1(self) -> None:
        # P=2000, D=0.5h → capacidad de servicio = 500×(1/0.5)=1000;
        # entries=1000; O_1 = (1000/1)×0.5×(1-exp(-2)) = 500×(1-exp(-2)).
        zone = make_zone(
            "a0000000-0000-0000-0000-000000000001",
            500,
            100.0,
            subtipo="foodtruck",
        )
        data = FoodV1Model().execute(make_context(zone)).data
        expected_stock = 500.0 * (1.0 - math.exp(-2.0))
        assert data["food_id"] == str(zone.id)
        assert data["occupied"] == pytest.approx(expected_stock)
        assert data["capacity"] == 500
        assert data["occupancy_ratio"] == pytest.approx(expected_stock / 500.0)
        assert data["free_ratio"] == pytest.approx(math.exp(-2.0))
        assert data["free_spaces"] == pytest.approx(500.0 - expected_stock)
        assert data["distance"] == pytest.approx(100.0)
        assert data["unabsorbed"] == pytest.approx(1000.0)

    def test_execute_does_not_invent_extra_outputs(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        data = FoodV1Model().execute(make_context(zone)).data
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

    def test_execute_rejects_non_food_zone(self) -> None:
        zone = make_zone(
            "a0000000-0000-0000-0000-000000000002",
            500,
            100.0,
            type="servicios",
            subtipo="banos",
        )
        with pytest.raises(ValueError):
            FoodV1Model().execute(make_context(zone))

    def test_execute_rejects_max_people_null(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        with pytest.raises(ValueError):
            FoodV1Model().execute(make_context(zone, max_people=None))

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
            FoodV1Model().execute(without_duration)


class TestFormulasPrincipales:
    def test_p_expected(self) -> None:
        model = FoodV1Model()
        assert model.p_expected(10_000, 0.30) == pytest.approx(3000.0)
        assert model.p_expected(8000, 0.50) == pytest.approx(4000.0)
        assert model.p_expected(8000, 0.0) == pytest.approx(0.0)

    def test_p_expected_intensity_above_one(self) -> None:
        # Intensidades > 1 no se rechazan (igual que Parking/Baños); la
        # validación de suma 1.0 es hipótesis de configuración (R8).
        assert FoodV1Model().p_expected(8000, 1.25) == pytest.approx(10_000.0)

    def test_duration_hours_conversion(self) -> None:
        model = FoodV1Model()
        assert model.duration_hours(60) == pytest.approx(1.0)
        assert model.duration_hours(20) == pytest.approx(1 / 3.0)
        assert model.duration_hours(45) == pytest.approx(0.75)

    def test_retention(self) -> None:
        model = FoodV1Model()
        d_eff = DOC_D_EFFECTIVE_HOURS
        assert model.retention(1.0, d_eff) == pytest.approx(
            math.exp(-650.0 / 350.0), abs=1e-9
        )
        assert model.retention(2.0, 4.0) == pytest.approx(math.exp(-0.5), abs=1e-9)

    def test_retention_zero_delta(self) -> None:
        assert FoodV1Model().retention(0.0, 4.0) == pytest.approx(1.0)

    def test_effective_duration_ejemplo_normativo(self) -> None:
        # §21: D_eff = 350 / (150+400+100) = 0.538 h ≈ 32.29 min.
        d_eff = FoodV1Model().effective_duration(
            [float(c) for c in DOC_CAPACITIES],
            [m / 60.0 for m in DOC_DURATIONS_MIN],
        )
        assert d_eff == pytest.approx(DOC_D_EFFECTIVE_HOURS)

    def test_effective_duration_zona_unica_degenera_a_d(self) -> None:
        assert FoodV1Model().effective_duration([200.0], [0.5]) == pytest.approx(0.5)

    def test_effective_duration_es_armonico_no_aritmetico(self) -> None:
        capacities = [float(c) for c in DOC_CAPACITIES]
        durations = [m / 60.0 for m in DOC_DURATIONS_MIN]
        harmonic = FoodV1Model().effective_duration(capacities, durations)
        arithmetic = sum(durations) / len(durations)
        assert harmonic != pytest.approx(arithmetic, abs=1e-6)
        assert harmonic < arithmetic

    def test_service_capacity_ejemplo_normativo(self) -> None:
        # §20: Σ [cap_i × Δt/D_i] = 150 + 400 + 100 = 650 personas/fase.
        scap = FoodV1Model().service_capacity_phase(
            [float(c) for c in DOC_CAPACITIES],
            [m / 60.0 for m in DOC_DURATIONS_MIN],
            DOC_DELTA_HOURS,
        )
        assert scap == pytest.approx(DOC_SERVICE_CAPACITY)

    def test_service_capacity_escala_lineal_con_delta(self) -> None:
        series_caps = [float(c) for c in DOC_CAPACITIES]
        series_durs = [m / 60.0 for m in DOC_DURATIONS_MIN]
        model = FoodV1Model()
        assert model.service_capacity_phase(series_caps, series_durs, 2.0) == (
            pytest.approx(2.0 * DOC_SERVICE_CAPACITY)
        )

    def test_temporal_step_primera_fase_ejemplo_normativo(self) -> None:
        # §24: entries=min(3000,650)=650; unabsorbed=2350;
        # contribution=(650/1)×(350/650)×(1-r)=350×(1-r).
        model = FoodV1Model()
        r = model.retention(DOC_DELTA_HOURS, DOC_D_EFFECTIVE_HOURS)
        result = model.temporal_step(
            0.0, 3000.0, DOC_SERVICE_CAPACITY, DOC_DELTA_HOURS,
            DOC_D_EFFECTIVE_HOURS,
        )
        assert result.p_expected == pytest.approx(3000.0)
        assert result.entries == pytest.approx(DOC_SERVICE_CAPACITY)
        assert result.unabsorbed == pytest.approx(3000.0 - 650.0)
        assert result.retention == pytest.approx(r)
        assert result.remain == pytest.approx(0.0)
        assert result.contribution == pytest.approx(
            350.0 * (1.0 - r), rel=1e-12
        )
        assert result.stock == pytest.approx(350.0 * (1.0 - r))

    def test_temporal_step_segunda_fasa_conserva_temporal(self) -> None:
        # V8: O_t = remain + contribution exactamente.
        model = FoodV1Model()
        o1 = 350.0 * (1.0 - model.retention(1.0, DOC_D_EFFECTIVE_HOURS))
        result = model.temporal_step(
            o1, 3000.0, DOC_SERVICE_CAPACITY, DOC_DELTA_HOURS,
            DOC_D_EFFECTIVE_HOURS,
        )
        assert result.remain == pytest.approx(o1 * result.retention, rel=1e-12)
        assert result.stock == pytest.approx(
            result.remain + result.contribution, rel=1e-12
        )

    def test_demanda_cero_decae_stock(self) -> None:
        # Intensity 0: sin llegadas, el stock solo decae exponencialmente.
        result = FoodV1Model().temporal_step(295.36, 0.0, 650.0, 1.0, 0.53846)
        assert result.entries == pytest.approx(0.0)
        assert result.contribution == pytest.approx(0.0)
        assert result.stock == pytest.approx(295.36 * result.retention)


class TestPermanenciaIntermedia:
    """Régimen intermedio entre Parking (acumula fuerte) y Baños (r≈0)."""

    def test_retencion_intermedia_en_rango_documento(self) -> None:
        # Tabla §16: r_t típico en Food V1 ∈ (0.01, 0.37); estrictamente
        # menor que Parking (≈0.78) y mayor que Baños (≈6e-6).
        r = FoodV1Model().retention(1.0, DOC_D_EFFECTIVE_HOURS)
        assert 0.01 < r < 0.37
        parking_like = FoodV1Model().retention(1.0, 4.0)
        banos_like = FoodV1Model().retention(1.0, 5 / 60.0)
        assert r < parking_like
        assert r > banos_like

    def test_alta_rotacion_reproduce_littles_law(self) -> None:
        # Caso límite §12: D_eff ≪ Δt ⇒ O_t ≈ entries × D_eff/Δt.
        model = FoodV1Model()
        d_eff = 1 / 60.0  # foodtrucks de 1 minuto
        delta = 1.0
        p_expected = 200.0
        service_capacity = 100.0 * (delta / d_eff)  # 6000 ≫ 200
        result = model.temporal_step(
            0.0, p_expected, service_capacity, delta, d_eff
        )
        assert result.stock == pytest.approx(
            p_expected * d_eff / delta, rel=1e-9
        )

    def test_rotacion_media_sesenta_por_ciento(self) -> None:
        # Caso límite §12: D_eff = Δt ⇒ O_t ≈ entries × (1-e^-1) ≈ 0.632.
        result = FoodV1Model().temporal_step(0.0, 800.0, 1000.0, 1.0, 1.0)
        assert result.stock == pytest.approx(800.0 * (1.0 - math.exp(-1.0)))

    def test_baja_rotacion_acumula_hasta_capacidad(self) -> None:
        zones = [
            make_zone("a0000000-0000-0000-0000-000000000001", 300, 100.0),
            make_zone("a0000000-0000-0000-0000-000000000002", 300, 400.0),
        ]
        durations = {z.id: 10.0 for z in zones}  # restaurantes lentos: 10 h
        phases = make_ten_phases(tuple(0.1 for _ in range(10)))
        results = FoodV1Model().simulate(phases, zones, 10_000, durations)
        stocks = [state.stock for state in results]
        assert all(a <= b + 1e-9 for a, b in zip(stocks, stocks[1:]))
        total_capacity = sum(float(z.capacity) for z in zones)
        for state in results:
            assert state.stock <= total_capacity + 1e-6


class TestLimitesDeCapacidad:
    """V1, V2 y V3 del documento."""

    def test_v1_p_expected_sin_tope_territorial(self) -> None:
        # La presión territorial NO se recorta: P_expected puede superar
        # ampliamente la capacidad de servicio.
        result = FoodV1Model().temporal_step(0.0, 100_000.0, 650.0, 1.0, 0.5)
        assert result.p_expected == pytest.approx(100_000.0)
        assert result.unabsorbed > 90_000.0

    def test_v2_entries_acotadas_por_capacidad_de_servicio(self) -> None:
        model = FoodV1Model()
        caps = [float(c) for c in DOC_CAPACITIES]
        durs = [m / 60.0 for m in DOC_DURATIONS_MIN]
        for p_expected in (10.0, 300.0, 650.0, 3_000.0, 50_000.0):
            scap = model.service_capacity_phase(caps, durs, 1.0)
            result = model.temporal_step(0.0, p_expected, scap, 1.0, 0.5)
            assert result.entries <= scap + 1e-9
            if p_expected <= scap:
                assert result.entries == pytest.approx(p_expected)

    def test_v2_simulate_entries_acotadas_en_todas_las_fases(self) -> None:
        zones = make_doc_zones()
        results = FoodV1Model().simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES),
            zones,
            DOC_MAX_PEOPLE,
            doc_durations_hours(zones),
        )
        for state in results:
            assert state.entries <= state.service_capacity_phase + 1e-9

    def test_v3_stock_acotado_por_capacidad_total(self) -> None:
        zones = make_doc_zones()
        results = FoodV1Model().simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES),
            zones,
            DOC_MAX_PEOPLE,
            doc_durations_hours(zones),
        )
        total_capacity = DOC_TOTAL_CAPACITY
        for state in results:
            assert state.stock <= total_capacity + 1e-6


class TestDistribucionEspacial:
    def test_ejemplo_normativo_24(self) -> None:
        # §24: foodtruck satura en 50, restaurante alcanza su tope 100 y el
        # patio absorbe el resto. Σ occupied == O_t (conservación exacta;
        # el cierre "Σ=291.5" del documento es artefacto ilustrativo R6).
        model = FoodV1Model()
        zones = make_doc_zones()
        phases = [make_phase(0, 60, DOC_INTENSITY, sequence=1)]
        results = model.simulate(
            phases, zones, DOC_MAX_PEOPLE, doc_durations_hours(zones)
        )
        state = results[0]
        o1 = state.stock
        assert o1 == pytest.approx(
            350.0 * (1.0 - math.exp(-13.0 / 7.0)), rel=1e-9
        )
        occupied = state.occupied
        assert occupied[zones[0].id] == pytest.approx(50.0, abs=1e-6)
        assert occupied[zones[2].id] == pytest.approx(100.0, abs=1e-6)
        assert occupied[zones[1].id] == pytest.approx(o1 - 150.0, abs=1e-6)
        assert sum(occupied.values()) == pytest.approx(o1, abs=1e-6)
        ratios = [
            model.indices(occupied[z.id], z.capacity)[0] for z in zones
        ]
        assert ratios[0] == pytest.approx(1.0)
        assert ratios[2] == pytest.approx(1.0)
        assert 0.0 < ratios[1] < 1.0

    def test_zona_cercana_preferida_sin_saturacion(self) -> None:
        near = make_zone("a0000000-0000-0000-0000-000000000001", 100, 100.0)
        far = make_zone("a0000000-0000-0000-0000-000000000002", 100, 900.0)
        occupied = FoodV1Model().distribute({}, [near, far], 40.0)
        assert occupied[near.id] > occupied[far.id]

    def test_contraccion_libera_menos_preferida_primero(self) -> None:
        zones = [
            make_zone("a0000000-0000-0000-0000-000000000001", 100, 100.0),
            make_zone("a0000000-0000-0000-0000-000000000002", 200, 400.0),
            make_zone("a0000000-0000-0000-0000-000000000003", 300, 900.0),
        ]
        prev = {
            zones[0].id: 80.0,
            zones[1].id: 160.0,
            zones[2].id: 240.0,
        }
        occupied = FoodV1Model().distribute(prev, zones, 380.0)
        # Se retira primero de la zona más lejana (menor w_i).
        assert occupied[zones[2].id] == pytest.approx(140.0, abs=1e-6)
        assert occupied[zones[0].id] == pytest.approx(80.0, abs=1e-6)
        assert occupied[zones[1].id] == pytest.approx(160.0, abs=1e-6)
        assert sum(occupied.values()) == pytest.approx(380.0, abs=1e-6)

    def test_alpha_cero_sin_efecto_de_distancia(self) -> None:
        zones = [
            make_zone("a0000000-0000-0000-0000-000000000001", 100, 100.0),
            make_zone("a0000000-0000-0000-0000-000000000002", 100, 900.0),
            make_zone("a0000000-0000-0000-0000-000000000003", 100, 2500.0),
        ]
        occupied = FoodV1Model(alpha=0.0).distribute({}, zones, 150.0)
        for zone in zones:
            assert occupied[zone.id] == pytest.approx(50.0, abs=0.1)

    def test_distribute_independiente_del_orden(self) -> None:
        zones = make_doc_zones()
        prev = {
            zones[0].id: 30.0,
            zones[1].id: 90.0,
            zones[2].id: 50.0,
        }
        model = FoodV1Model()
        direct = model.distribute(prev, zones, 280.0)
        flipped = model.distribute(prev, list(reversed(zones)), 280.0)
        for zone in zones:
            assert flipped[zone.id] == pytest.approx(direct[zone.id], abs=1e-9)


class TestInvariantes:
    """V4-V8 y V10-V12 sobre simulaciones completas."""

    def _simulate_scenario(self) -> tuple[FoodV1Model, list[Zone], list]:
        model = FoodV1Model()
        zones = make_doc_zones()
        results = model.simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES),
            zones,
            DOC_MAX_PEOPLE,
            doc_durations_hours(zones),
        )
        return model, zones, results

    def test_estado_inicial_cero(self) -> None:
        initial = FoodV1Model().initial_occupied(make_doc_zones())
        assert sum(initial.values()) == pytest.approx(0.0)

    def test_v4_v5_ocupacion_acotada_y_conservada(self) -> None:
        _, zones, results = self._simulate_scenario()
        capacities = {zone.id: float(zone.capacity) for zone in zones}
        for state in results:
            for zone_id, occupied in state.occupied.items():
                assert 0.0 <= occupied <= capacities[zone_id] + 1e-9
            # El stock nunca supera ΣC (V3), por lo que la conservación es
            # exacta: Σ occupied_i(t) == O_t.
            assert sum(state.occupied.values()) == pytest.approx(
                state.stock, abs=1e-6
            )

    def test_v6_unabsorbed_residual_exacto(self) -> None:
        _, _, results = self._simulate_scenario()
        for state in results:
            assert state.unabsorbed == pytest.approx(
                max(0.0, state.p_expected - state.entries), abs=1e-9
            )

    def test_v7_unabsorbed_no_persiste_como_backlog(self) -> None:
        # Fase 1 con demanda desbordada (unabsorbed grande), fase 2 sin
        # demanda: si unabsorbed fuese backlog, la fase 2 heredaría stock
        # extra. Solo puede decaer por retención.
        model = FoodV1Model()
        zones = make_doc_zones()
        durations = doc_durations_hours(zones)
        phases = [
            make_phase(0, 60, 0.90, sequence=1),
            make_phase(60, 120, 0.0, sequence=2),
        ]
        results = model.simulate(phases, zones, DOC_MAX_PEOPLE, durations)
        first, second = results
        assert first.unabsorbed > 0.0
        assert second.p_expected == pytest.approx(0.0)
        assert second.unabsorbed == pytest.approx(0.0)
        assert second.contribution == pytest.approx(0.0)
        assert second.remain == pytest.approx(second.stock, rel=1e-12)
        assert second.stock == pytest.approx(
            first.stock * model.retention(1.0, first.d_effective_hours),
            rel=1e-9,
        )

    def test_v12_stock_distinto_de_flujo_y_nivel(self) -> None:
        _, _, results = self._simulate_scenario()
        saturated = [s for s in results if s.unabsorbed > 0.0]
        assert saturated, "el escenario debe tener fases saturadas"
        for state in saturated:
            assert state.stock != pytest.approx(state.entries, abs=1.0)
            assert state.stock != pytest.approx(state.p_expected, abs=1.0)

    def test_v10_distancia_afecta_distribucion_no_total(self) -> None:
        zones = make_doc_zones()
        phases = make_ten_phases(SCENARIO_A_INTENSITIES)
        durations = doc_durations_hours(zones)
        near_model = FoodV1Model(alpha=0.0)
        far_model = FoodV1Model(alpha=DEFAULT_ALPHA)
        for state_near, state_far in zip(
            near_model.simulate(phases, zones, DOC_MAX_PEOPLE, durations),
            far_model.simulate(phases, zones, DOC_MAX_PEOPLE, durations),
        ):
            assert state_near.stock == pytest.approx(state_far.stock, rel=1e-9)
            assert sum(state_near.occupied.values()) == pytest.approx(
                sum(state_far.occupied.values()), abs=1e-6
            )

    def test_v11_capacidad_afecta_absorcion_no_demanda(self) -> None:
        model = FoodV1Model()
        small = [make_zone("a0000000-0000-0000-0000-000000000001", 50, 100.0)]
        large = [make_zone("a0000000-0000-0000-0000-000000000002", 5000, 100.0)]
        phases = [make_phase(0, 60, 0.30, sequence=1)]
        duration = {small[0].id: 1 / 3.0}
        large_duration = {large[0].id: 1 / 3.0}
        small_state = model.simulate(phases, small, DOC_MAX_PEOPLE, duration)[0]
        large_state = model.simulate(
            phases, large, DOC_MAX_PEOPLE, large_duration
        )[0]
        assert small_state.p_expected == pytest.approx(large_state.p_expected)
        assert small_state.service_capacity_phase < large_state.service_capacity_phase
        assert small_state.unabsorbed > 0.0
        assert large_state.unabsorbed == pytest.approx(0.0)

    def test_fases_se_evaluan_en_orden_cronologico(self) -> None:
        zones = make_doc_zones()
        unordered = [
            make_phase(120, 180, 0.20, sequence=3),
            make_phase(0, 60, 0.60, sequence=1),
            make_phase(60, 120, 0.40, sequence=2),
        ]
        results = FoodV1Model().simulate(
            unordered, zones, DOC_MAX_PEOPLE, doc_durations_hours(zones)
        )
        assert [state.index for state in results] == [1, 2, 3]
        assert results[0].p_expected == pytest.approx(6000.0)
        assert results[1].p_expected == pytest.approx(4000.0)
        assert results[2].p_expected == pytest.approx(2000.0)


class TestDeterminismo:
    def test_execute_determinista(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        model = FoodV1Model()
        context = make_context(zone)
        first = model.execute(context).data
        for _ in range(5):
            assert model.execute(context).data == first

    def test_simulate_determinista(self) -> None:
        zones = make_doc_zones()
        model = FoodV1Model()
        first = model.simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES),
            zones,
            DOC_MAX_PEOPLE,
            doc_durations_hours(zones),
        )
        second = model.simulate(
            make_ten_phases(SCENARIO_A_INTENSITIES),
            zones,
            DOC_MAX_PEOPLE,
            doc_durations_hours(zones),
        )
        for a, b in zip(first, second):
            assert a == b


class TestRegresionMotoresExistentes:
    def test_bathroom_v1_unchanged(self) -> None:
        from src.domain.models.bathroom_v1_model import BathroomV1Model

        result = BathroomV1Model().temporal_step(1600.0, 2800.0, 10000.0, 1.0, 4.0)
        assert result.remain == pytest.approx(1246.08, abs=0.1)
        assert result.entries == pytest.approx(2500.0, abs=0.1)
        assert result.stock == pytest.approx(2800.0 * 4.0, abs=0.1)
        assert result.unabsorbed == pytest.approx(300.0, abs=0.1)

    def test_parking_v1_unchanged(self) -> None:
        from src.domain.models.parking_v1_model import ParkingV1Model

        parking_zone = Zone(
            id=UUID("a0000000-0000-0000-0000-000000000009"),
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
    def test_p_expected_sin_max_people(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().p_expected(None, 0.25)

    def test_p_expected_max_people_negativo(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().p_expected(-1, 0.25)

    def test_p_expected_max_people_bool(self) -> None:
        with pytest.raises(TypeError):
            FoodV1Model().p_expected(True, 0.25)

    def test_p_expected_sin_intensity(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().p_expected(8000, None)

    def test_p_expected_intensity_negativa(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().p_expected(8000, -0.1)

    def test_p_expected_tipo_invalido(self) -> None:
        with pytest.raises(TypeError):
            FoodV1Model().p_expected("8000", 0.25)

    def test_duration_hours_none(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().duration_hours(None)

    def test_duration_hours_cero(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().duration_hours(0)

    def test_duration_hours_negativo(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().duration_hours(-20)

    def test_duration_hours_bool(self) -> None:
        with pytest.raises(TypeError):
            FoodV1Model().duration_hours(True)

    def test_effective_duration_series_vacias(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().effective_duration([], [])

    def test_effective_duration_longitudes_distintas(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().effective_duration([100.0], [0.5, 1.0])

    def test_effective_duration_capacidad_cero(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().effective_duration([0.0], [0.5])

    def test_effective_duration_permancia_cero(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().effective_duration([100.0], [0.0])

    def test_effective_duration_elemento_invalido(self) -> None:
        with pytest.raises(TypeError):
            FoodV1Model().effective_duration(["100"], [0.5])

    def test_service_capacity_delta_cero(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().service_capacity_phase([100.0], [0.5], 0.0)

    def test_service_capacity_delta_negativo(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().service_capacity_phase([100.0], [0.5], -1.0)

    def test_service_capacity_series_vacias(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().service_capacity_phase([], [], 1.0)

    def test_retention_delta_negativo(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().retention(-1.0, 0.5)

    def test_retention_duration_cero(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().retention(1.0, 0.0)

    def test_retention_duration_none(self) -> None:
        with pytest.raises(TypeError):
            FoodV1Model().retention(1.0, None)

    def test_temporal_step_prev_stock_negativo(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().temporal_step(-1.0, 1000.0, 650.0, 1.0, 0.5)

    def test_temporal_step_p_expected_negativo(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().temporal_step(0.0, -5.0, 650.0, 1.0, 0.5)

    def test_temporal_step_capacidad_servicio_cero(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().temporal_step(0.0, 1000.0, 0.0, 1.0, 0.5)

    def test_temporal_step_delta_cero(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().temporal_step(0.0, 1000.0, 650.0, 0.0, 0.5)

    def test_temporal_step_delta_negativo(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().temporal_step(0.0, 1000.0, 650.0, -1.0, 0.5)

    def test_distribute_stock_negativo(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        with pytest.raises(ValueError):
            FoodV1Model().distribute({}, [zone], -1.0)

    def test_distribute_sin_zonas(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().distribute({}, [], 100.0)

    def test_distribute_alpha_negativo(self) -> None:
        zone = make_zone("a0000000-0000-0000-0000-000000000001", 500, 100.0)
        with pytest.raises(ValueError):
            FoodV1Model().distribute({}, [zone], 100.0, alpha=-0.1)

    def test_indices_occupied_negativo(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().indices(-1.0, 500)

    def test_indices_capacidad_cero(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().indices(0.0, 0)

    def test_constructor_alpha_negativo(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model(alpha=-0.001)

    def test_constructor_alpha_bool(self) -> None:
        with pytest.raises(TypeError):
            FoodV1Model(alpha=True)

    def test_simulate_sin_fases(self) -> None:
        zones = make_doc_zones()
        with pytest.raises(ValueError):
            FoodV1Model().simulate([], zones, DOC_MAX_PEOPLE,
                                   doc_durations_hours(zones))

    def test_simulate_sin_zonas(self) -> None:
        with pytest.raises(ValueError):
            FoodV1Model().simulate(
                make_ten_phases(SCENARIO_A_INTENSITIES), [], DOC_MAX_PEOPLE, {}
            )

    def test_simulate_max_people_none(self) -> None:
        zones = make_doc_zones()
        with pytest.raises(ValueError):
            FoodV1Model().simulate(
                make_ten_phases(SCENARIO_A_INTENSITIES),
                zones,
                None,
                doc_durations_hours(zones),
            )

    def test_simulate_max_people_tipo_invalido(self) -> None:
        zones = make_doc_zones()
        with pytest.raises(TypeError):
            FoodV1Model().simulate(
                make_ten_phases(SCENARIO_A_INTENSITIES),
                zones,
                "10000",
                doc_durations_hours(zones),
            )

    def test_simulate_duracion_faltante_para_zona(self) -> None:
        zones = make_doc_zones()
        durations = doc_durations_hours(zones)
        del durations[zones[1].id]
        with pytest.raises(ValueError):
            FoodV1Model().simulate(
                make_ten_phases(SCENARIO_A_INTENSITIES),
                zones,
                DOC_MAX_PEOPLE,
                durations,
            )

    def test_simulate_duracion_cero_para_zona(self) -> None:
        zones = make_doc_zones()
        durations = doc_durations_hours(zones)
        durations[zones[0].id] = 0.0
        with pytest.raises(ValueError):
            FoodV1Model().simulate(
                make_ten_phases(SCENARIO_A_INTENSITIES),
                zones,
                DOC_MAX_PEOPLE,
                durations,
            )

    def test_simulate_intensity_null_en_fase(self) -> None:
        zones = make_doc_zones()
        phases = [make_phase(0, 60, None, sequence=1)]
        with pytest.raises(ValueError):
            FoodV1Model().simulate(
                phases, zones, DOC_MAX_PEOPLE, doc_durations_hours(zones)
            )
