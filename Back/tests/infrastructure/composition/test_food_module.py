"""ETAPA 3 Food V1 — FoodModule: ejecución de simulate() sobre el universo
físico real.

La infraestructura de BD se simula con AsyncMock (mismo patrón que el resto
de la suite): no se accede a base de datos alguna, no se usa BD local ni Neon.
Se verifica que FoodV1Model recibe TODAS las zonas type="comida" (todos los
subtipos), todas las fases, max_people (AttendanceLevel) y las permanencias
resueltas desde ServiceConfig POR SUBTIPO (override → default, en MINUTOS,
convertidas a HORAS una sola vez en la frontera; D_eff la calcula el modelo).
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.zone import Zone
from src.domain.models.food_v1_model import FoodV1Model
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.infrastructure.composition.food_module import (
    FOOD_SUBTIPOS,
    FOOD_ZONE_TYPE,
    FoodModule,
    FoodSimulationResult,
    _load_food_zones,
    derive_food_zone_state,
    merge_food_into_prediction,
)

EVENT_ID = "event-food-1"
DAY_ID = "11111111-1111-1111-1111-111111111111"
OP_ID = "22222222-2222-2222-2222-222222222222"
ATTENDANCE_ID = "55555555-5555-5555-5555-555555555555"

ZT_IDS = {
    "comida": "33333333-3333-3333-3333-333333333333",
    "bano": "34444444-4444-4444-4444-444444444444",
    "estacionamiento": "35555555-5555-5555-5555-555555555555",
}

FOOD_IDS = {
    "foodtruck": "a0000000-0000-0000-0000-000000000001",
    "patio": "a0000000-0000-0000-0000-000000000002",
    "restaurante": "a0000000-0000-0000-0000-000000000003",
}

NON_FOOD_IDS = {
    "estacionamiento": "b0000000-0000-0000-0000-000000000001",
    "banos": "b0000000-0000-0000-0000-000000000002",
    "hidratacion": "b0000000-0000-0000-0000-000000000003",
}

PHASE_IDS = {
    "p1": "c0000000-0000-0000-0000-000000000001",
    "p2": "c0000000-0000-0000-0000-000000000002",
    "p3": "c0000000-0000-0000-0000-000000000003",
}

REF_LAT = -31.4135
REF_LNG = -64.1811

# (subtipo, capacity, latitude, longitude)
FOOD_SPECS = {
    "foodtruck": ("foodtruck", 150, -31.4135, -64.1811),
    "patio": ("patio_de_comidas", 400, -31.42, -64.19),
    "restaurante": ("restaurante", 200, -31.43, -64.20),
}

MAX_PEOPLE = 10000
# Permanencias por subtipo en minutos (defaults del diseño PARTE 4).
DURATIONS_MIN = {
    "foodtruck": 20,
    "patio_de_comidas": 30,
    "restaurante": 60,
}
PHASES_SPEC = [
    (PHASE_IDS["p1"], 600, 720, 0.25),
    (PHASE_IDS["p2"], 720, 840, 0.50),
    (PHASE_IDS["p3"], 840, 960, 0.75),
]

TIMESTAMP = datetime(2026, 7, 15, 15, 0, tzinfo=timezone.utc)


def _scalars_result(models):
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.__iter__.return_value = iter(models)
    scalars_mock.all.return_value = list(models)
    result.scalars = MagicMock(return_value=scalars_mock)
    return result


def _scalar_one_result(model):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=model)
    return result


def _one_result(row):
    result = MagicMock()
    result.one_or_none = MagicMock(return_value=row)
    return result


def _zone_row(zone_id, name, ztype, subtipo, capacity, available_capacity, lat, lng):
    return SimpleNamespace(
        id=zone_id,
        name=name,
        type=ztype,
        subtipo=subtipo,
        capacity=capacity,
        available_capacity=available_capacity,
        latitude=lat,
        longitude=lng,
    )


def _food_zone_rows():
    rows = []
    for key in ("foodtruck", "patio", "restaurante"):
        subtipo, capacity, lat, lng = FOOD_SPECS[key]
        rows.append(
            _zone_row(
                FOOD_IDS[key],
                f"Comida {key}",
                "comida",
                subtipo,
                capacity,
                capacity,
                lat,
                lng,
            )
        )
    return rows


def _non_food_zone_rows():
    return [
        _zone_row(
            NON_FOOD_IDS["estacionamiento"],
            "Parking Norte",
            "estacionamiento",
            None,
            300,
            300,
            -31.4135,
            -64.1811,
        ),
        _zone_row(
            NON_FOOD_IDS["banos"],
            "Banos Sector",
            "servicios",
            "banos",
            200,
            200,
            -31.42,
            -64.19,
        ),
        _zone_row(
            NON_FOOD_IDS["hidratacion"],
            "Fuente Agua",
            "servicios",
            "hidratacion",
            150,
            150,
            -31.43,
            -64.20,
        ),
    ]


def _ed_row(phases_spec=None):
    return SimpleNamespace(
        id=DAY_ID,
        date=date(2026, 7, 15),
        attendance_level_id=ATTENDANCE_ID,
        operational_profile_id=UUID("99999999-0000-0000-0000-000000000001"),
        operational_start_min=600,
        operational_end_min=960,
        estimated_vehicles=None,
        average_parking_duration=None,
        phases=[
            SimpleNamespace(
                id=phase_id,
                operational_phase_id=OP_ID,
                start_min=start_min,
                end_min=end_min,
                intensity=intensity,
            )
            for phase_id, start_min, end_min, intensity in (
                PHASES_SPEC if phases_spec is None else phases_spec
            )
        ],
    )


def _attendance_row(max_people=MAX_PEOPLE):
    return SimpleNamespace(
        id=ATTENDANCE_ID,
        event_id=EVENT_ID,
        name="Normal",
        min_people=5000,
        max_people=max_people,
    )


def _service_config_rows(**overrides):
    """Filas de ServiceConfig por subtipo: {key: (override_min|None, default_min|None)}."""
    base = {key: (None, minutes) for key, minutes in DURATIONS_MIN.items()}
    base.update(overrides)
    return {
        key: (
            (
                SimpleNamespace(average_duration_min=override)
                if override is not None
                else None
            ),
            (
                SimpleNamespace(average_duration_min=default)
                if default is not None
                else None
            ),
        )
        for key, (override, default) in base.items()
    }


def _mock_session(zone_rows, ed_row, *, attendance_row=None, config_rows=None):
    """Mock de sesión con despacho por tabla (SQL).

    `resolve_active_event_day` consulta event_days dos veces (hoy y ayer):
    ambas devuelven `ed_row`. Para `service_configs` se despacha por subtipo
    compilado (literal_binds): primero intenta override por jornada y luego
    default global (`IS NULL`), exactamente como `_resolve_service_duration`.
    """
    session = AsyncMock()
    captured_stmts = []
    zone_type_rows = [
        SimpleNamespace(slug="comida", id=ZT_IDS["comida"]),
        SimpleNamespace(slug="bano", id=ZT_IDS["bano"]),
        SimpleNamespace(slug="estacionamiento", id=ZT_IDS["estacionamiento"]),
    ]
    ref_row = SimpleNamespace(
        reference_point_latitude=REF_LAT,
        reference_point_longitude=REF_LNG,
    )
    rows_by_key = config_rows or {}

    async def fake_execute(stmt, *args, **kwargs):
        captured_stmts.append(stmt)
        sql = str(stmt)
        if "zone_types" in sql:
            return _scalars_result(zone_type_rows)
        if "events" in sql:
            return _one_result(ref_row)
        if "zones" in sql:
            return _scalars_result(zone_rows)
        if "event_days" in sql:
            return _scalar_one_result(ed_row)
        if "attendance_levels" in sql:
            return _scalar_one_result(attendance_row)
        if "service_configs" in sql:
            compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
            match = re.search(
                r"coalesce\(service_configs\.subtipo, ''\) = '([^']*)'", compiled
            )
            key = match.group(1) if match else ""
            override_row, default_row = rows_by_key.get(key, (None, None))
            if re.search(r"IS NULL", compiled, flags=re.IGNORECASE):
                return _scalar_one_result(default_row)
            return _scalar_one_result(override_row)
        raise AssertionError(f"unexpected statement: {sql}")

    session.execute = fake_execute
    session.captured_stmts = captured_stmts
    return session


def _expected_food_ids():
    return {UUID(FOOD_IDS[key]) for key in FOOD_IDS}


def _total_capacity():
    return sum(spec[1] for spec in FOOD_SPECS.values())


def _d_effective_hours():
    # §21: promedio armónico ponderado por capacidad, en horas.
    capacities = [float(spec[1]) for spec in FOOD_SPECS.values()]
    durations_h = [
        DURATIONS_MIN[spec[0]] / 60.0 for spec in FOOD_SPECS.values()
    ]
    return sum(capacities) / sum(c / d for c, d in zip(capacities, durations_h))


class TestFoodModuleDataFlow:
    async def test_all_food_zones_delivered(self) -> None:
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )

        assert result is not None
        assert len(result.food_zones) == 3
        assert {zone.id for zone in result.food_zones} == _expected_food_ids()

    async def test_non_food_zones_excluded_from_module(self) -> None:
        rows = _food_zone_rows() + _non_food_zone_rows()
        session = _mock_session(
            rows,
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )

        assert result is not None
        delivered = {zone.id for zone in result.food_zones}
        assert delivered == _expected_food_ids()
        assert not delivered.intersection({UUID(v) for v in NON_FOOD_IDS.values()})

    async def test_zones_query_filters_only_by_type_comida(self) -> None:
        rows = _food_zone_rows() + _non_food_zone_rows()
        session = _mock_session(
            rows,
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )

        zones_stmt = session.captured_stmts[2]
        compiled = str(zones_stmt.compile(compile_kwargs={"literal_binds": True}))
        # SQLAlchemy compila "WHERE" tras un salto de línea; se extrae la
        # cláusula con límite de palabra en lugar de split por espacios.
        where_match = re.split(r"\bWHERE\b", compiled, maxsplit=1)
        assert len(where_match) == 2
        where_part = where_match[1]
        assert "zones.type" in where_part
        assert "'comida'" in where_part
        # Todos los subtipos entran: NO hay filtro por zones.subtipo.
        assert "zones.subtipo" not in where_part

    async def test_each_zone_preserves_physical_fields(self) -> None:
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None

        by_id = {zone.id: zone for zone in result.food_zones}
        for key in ("foodtruck", "patio", "restaurante"):
            subtipo, capacity, lat, lng = FOOD_SPECS[key]
            zone = by_id[UUID(FOOD_IDS[key])]
            assert zone.capacity == capacity
            assert zone.type == "comida"
            assert zone.subtipo == subtipo
            assert zone.latitude == lat
            assert zone.longitude == lng

    async def test_reference_point_distance_computed_per_zone(self) -> None:
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None

        distances = {
            zone.id: zone.reference_point_distance for zone in result.food_zones
        }
        assert distances[UUID(FOOD_IDS["foodtruck"])] == 0.0
        for zone in result.food_zones:
            assert zone.reference_point_distance is not None
            assert zone.reference_point_distance >= 0.0

    async def test_full_phase_sequence_delivered(self) -> None:
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None

        assert len(result.phases) == 3
        assert [p.start_min for p in result.phases] == [600, 720, 840]
        assert [p.end_min for p in result.phases] == [720, 840, 960]
        assert [p.intensity for p in result.phases] == [0.25, 0.50, 0.75]

    async def test_max_people_arrives_from_attendance_level(self) -> None:
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.max_people == MAX_PEOPLE

    async def test_durations_resolved_per_subtipo_in_minutes(self) -> None:
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.durations_min == {
            "foodtruck": 20,
            "patio_de_comidas": 30,
            "restaurante": 60,
        }

    async def test_durations_converted_min_to_hours_per_zone(self) -> None:
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.durations_hours[UUID(FOOD_IDS["foodtruck"])] == (
            pytest.approx(20 / 60.0)
        )
        assert result.durations_hours[UUID(FOOD_IDS["patio"])] == (
            pytest.approx(30 / 60.0)
        )
        assert result.durations_hours[UUID(FOOD_IDS["restaurante"])] == (
            pytest.approx(60 / 60.0)
        )

    async def test_d_effective_hours_matches_model_formula(self) -> None:
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.d_effective_hours == pytest.approx(_d_effective_hours())
        for phase in result.phase_results:
            assert phase.d_effective_hours == pytest.approx(_d_effective_hours())

    async def test_service_config_override_takes_precedence_over_default(self) -> None:
        config_rows = _service_config_rows(foodtruck=(15, 30))
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=config_rows,
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.durations_min["foodtruck"] == 15

    async def test_service_config_falls_back_to_default(self) -> None:
        config_rows = _service_config_rows(restaurante=(None, 45))
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=config_rows,
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.durations_min["restaurante"] == 45

    async def test_service_config_lookup_uses_normalized_subtipo(self) -> None:
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None

        config_sqls = [
            str(stmt.compile(compile_kwargs={"literal_binds": True}))
            for stmt in session.captured_stmts
            if "service_configs" in str(stmt)
        ]
        assert any(
            "coalesce(service_configs.subtipo, '')" in sql for sql in config_sqls
        )
        assert any("= 'foodtruck'" in sql for sql in config_sqls)
        assert any("= 'patio_de_comidas'" in sql for sql in config_sqls)

    async def test_food_zones_resolve_zone_type_id_from_catalog_slug(self) -> None:
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert all(
            zone.zone_type_id == UUID(ZT_IDS["comida"])
            for zone in result.food_zones
        )

    async def test_missing_zone_type_slug_raises_clear_error(self) -> None:
        session = AsyncMock()
        rows = _food_zone_rows()
        session.execute = AsyncMock(return_value=_scalars_result(rows))

        with pytest.raises(ValueError, match="ZoneType slug 'comida' not found"):
            await _load_food_zones(
                session,
                EVENT_ID,
                {"transporte": UUID(ZT_IDS["estacionamiento"])},
                REF_LAT,
                REF_LNG,
            )


class TestFoodModuleSimulation:
    async def _execute(self):
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        return result

    async def test_simulate_executes_multiple_zones_and_phases(self) -> None:
        result = await self._execute()
        assert len(result.phase_results) == 3
        assert [phase.index for phase in result.phase_results] == [1, 2, 3]

    async def test_each_food_zone_has_result_in_every_phase(self) -> None:
        result = await self._execute()
        expected = _expected_food_ids()
        for phase in result.phase_results:
            assert set(phase.occupied.keys()) == expected

    async def test_first_phase_starts_from_zero(self) -> None:
        result = await self._execute()
        first = result.phase_results[0]
        model = FoodV1Model()
        delta_hours = 2.0
        p_expected = MAX_PEOPLE * PHASES_SPEC[0][3]
        service_capacity = model.service_capacity_phase(
            [float(spec[1]) for spec in FOOD_SPECS.values()],
            [DURATIONS_MIN[spec[0]] / 60.0 for spec in FOOD_SPECS.values()],
            delta_hours,
        )
        temporal = model.temporal_step(
            0.0, p_expected, service_capacity, delta_hours, _d_effective_hours()
        )
        assert first.remain == pytest.approx(0.0, abs=1e-9)
        assert first.p_expected == pytest.approx(p_expected)
        assert first.stock == pytest.approx(temporal.stock, rel=1e-12)

    async def test_invariants(self) -> None:
        result = await self._execute()
        capacities = {
            zone.id: float(zone.capacity) for zone in result.food_zones
        }
        total_capacity = _total_capacity()
        d_eff = _d_effective_hours()
        prev_stock = 0.0
        for phase in result.phase_results:
            occupied_sum = sum(phase.occupied.values())
            # V5 conservación exacta y V3 acotación por capacidad total.
            assert occupied_sum == pytest.approx(phase.stock, abs=1e-6)
            assert phase.stock <= total_capacity + 1e-6
            # V6 residual instantáneo.
            assert phase.unabsorbed == pytest.approx(
                max(0.0, phase.p_expected - phase.entries), abs=1e-6
            )
            # V4 topes por zona.
            for zone_id, occupied in phase.occupied.items():
                assert 0.0 <= occupied <= capacities[zone_id]
            # V8 ecuación exponencial fase a fase.
            spec = PHASES_SPEC[phase.index - 1]
            delta_hours = (spec[2] - spec[1]) / 60.0
            r = math.exp(-delta_hours / d_eff)
            assert phase.remain == pytest.approx(prev_stock * r, rel=1e-9)
            expected_contribution = (
                phase.entries / delta_hours
            ) * d_eff * (1.0 - r)
            assert phase.contribution == pytest.approx(
                expected_contribution, rel=1e-9
            )
            prev_stock = phase.stock

    async def test_determinism(self) -> None:
        session_a = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        session_b = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        result_a = await FoodModule(session_a).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        result_b = await FoodModule(session_b).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result_a is not None
        assert result_b is not None

        assert result_a.food_zones == result_b.food_zones
        assert result_a.phases == result_b.phases
        assert result_a.phase_results == result_b.phase_results


class TestFoodModuleEdges:
    async def test_no_food_zones_returns_none(self) -> None:
        session = _mock_session(_non_food_zone_rows(), _ed_row())
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is None

    async def test_no_event_day_returns_none(self) -> None:
        session = _mock_session(
            _food_zone_rows(),
            None,
            attendance_row=_attendance_row(),
        )
        result = await FoodModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is None

    async def test_missing_max_people_raises(self) -> None:
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(max_people=None),
            config_rows=_service_config_rows(),
        )
        with pytest.raises(ValueError):
            await FoodModule(session).execute(
                timestamp=TIMESTAMP,
                event_id=EVENT_ID,
            )

    async def test_missing_attendance_level_raises(self) -> None:
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=None,
            config_rows=_service_config_rows(),
        )
        with pytest.raises(ValueError):
            await FoodModule(session).execute(
                timestamp=TIMESTAMP,
                event_id=EVENT_ID,
            )

    async def test_missing_service_config_raises(self) -> None:
        config_rows = _service_config_rows()
        del config_rows["restaurante"]
        session = _mock_session(
            _food_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=config_rows,
        )
        with pytest.raises(ValueError):
            await FoodModule(session).execute(
                timestamp=TIMESTAMP,
                event_id=EVENT_ID,
            )

    async def test_unknown_subtipo_raises_clear_error(self) -> None:
        legacy_rows = [
            _zone_row(
                "a0000000-0000-0000-0000-000000000009",
                "Puesto Legacy",
                "comida",
                "rapido",
                100,
                100,
                -31.41,
                -64.18,
            )
        ]
        session = _mock_session(
            legacy_rows,
            _ed_row(),
            attendance_row=_attendance_row(),
            config_rows=_service_config_rows(),
        )
        with pytest.raises(ValueError, match="unknown food subtipo 'rapido'"):
            await FoodModule(session).execute(
                timestamp=TIMESTAMP,
                event_id=EVENT_ID,
            )


class TestLoadFoodZones:
    async def test_filters_to_food_only(self) -> None:
        session = AsyncMock()
        rows = _food_zone_rows() + _non_food_zone_rows()
        session.execute = AsyncMock(return_value=_scalars_result(rows))

        zones = await _load_food_zones(
            session,
            EVENT_ID,
            {slug: UUID(zt_id) for slug, zt_id in ZT_IDS.items()},
            REF_LAT,
            REF_LNG,
        )

        assert len(zones) == 3
        assert {zone.id for zone in zones} == _expected_food_ids()
        for zone in zones:
            assert isinstance(zone, Zone)
            assert zone.type == FOOD_ZONE_TYPE
            assert zone.subtipo in FOOD_SUBTIPOS
            assert zone.capacity > 0
            assert zone.latitude is not None
            assert zone.longitude is not None


class TestMergeFoodIntoPrediction:
    OTHER_ID = UUID("d0000000-0000-0000-0000-000000000001")
    BANOS_ID = UUID("d0000000-0000-0000-0000-000000000002")

    def _food_zones(self) -> tuple[Zone, ...]:
        return tuple(
            Zone(
                id=UUID(FOOD_IDS[key]),
                name=f"Comida {key}",
                zone_type_id=UUID(ZT_IDS["comida"]),
                capacity=FOOD_SPECS[key][1],
                type="comida",
                subtipo=FOOD_SPECS[key][0],
                reference_point_distance=100.0 * (i + 1),
            )
            for i, key in enumerate(("foodtruck", "patio", "restaurante"))
        )

    def _base_prediction(
        self, food_zones: tuple[Zone, ...], active_phase_id: UUID
    ) -> TerritorialPrediction:
        states = [
            ZoneState(
                zone_id=zone.id,
                operational_state="NORMAL",
                saturation_level=0.99,
                availability=0,
                type=zone.type,
                subtipo=zone.subtipo,
            )
            for zone in food_zones
        ]
        states.append(
            ZoneState(
                zone_id=self.OTHER_ID,
                operational_state="NORMAL",
                saturation_level=0.10,
                availability=270,
                type="estacionamiento",
                subtipo=None,
            )
        )
        states.append(
            ZoneState(
                zone_id=self.BANOS_ID,
                operational_state="CRITICO",
                saturation_level=0.80,
                availability=4,
                type="servicios",
                subtipo="banos",
            )
        )
        return TerritorialPrediction(
            timestamp=datetime(2026, 7, 15, 12, 0),
            zone_states=states,
            active_phase_id=active_phase_id,
            active_event_day_phase_id=active_phase_id,
        )

    def _phases(self) -> tuple[EventDayPhase, ...]:
        return tuple(
            EventDayPhase(
                id=UUID(phase_id),
                event_day_id=UUID(DAY_ID),
                operational_phase_id=UUID(OP_ID),
                start_min=start,
                end_min=end,
                intensity=intensity,
            )
            for phase_id, start, end, intensity in PHASES_SPEC
        )

    def _food_result(
        self, food_zones: tuple[Zone, ...], active_phase_id: UUID
    ) -> FoodSimulationResult:
        durations = {
            zone.id: DURATIONS_MIN[zone.subtipo] / 60.0 for zone in food_zones
        }
        phases = self._phases()
        phase_results = tuple(
            FoodV1Model().simulate(phases, food_zones, MAX_PEOPLE, durations)
        )
        return FoodSimulationResult(
            event_id=EVENT_ID,
            timestamp=datetime(2026, 7, 15, 12, 0),
            food_zones=food_zones,
            phases=phases,
            max_people=MAX_PEOPLE,
            durations_min=dict(DURATIONS_MIN),
            durations_hours=durations,
            d_effective_hours=phase_results[0].d_effective_hours,
            phase_results=phase_results,
        )

    def test_replaces_only_food_zone_states(self) -> None:
        food_zones = self._food_zones()
        last_phase_id = UUID(PHASE_IDS["p3"])
        base = self._base_prediction(food_zones, last_phase_id)
        result = self._food_result(food_zones, last_phase_id)

        # Actualizar base para que tenga projected_density = capacity × 0.3 (sin
        # evento, density_factor=0.3), reflejando el uso real: una zona sin impacto
        # con demanda moderada muestra baja ocupación, NO aparecer colapsada.
        for zs in base.zone_states:
            for zone in food_zones:
                if zs.zone_id == zone.id:
                    zs._projected_density = int(zone.capacity * 0.3)
                    break

        merged = merge_food_into_prediction(base, result)
        by_id = {zs.zone_id: zs for zs in merged.zone_states}

        phase_state = result.phase_results[-1]
        for zone in food_zones:
            state = by_id[zone.id]

            # SIN EVENTO: occupancy = source_occupied / capacity = 0.3,
            # free = capacity * 0.7
            expected_ratio = 0.3
            expected_free = float(zone.capacity) * 0.7

            assert state.saturation_level == pytest.approx(expected_ratio)
            assert state.availability == round(expected_free)
            assert state.model_result is not None
            assert state.model_result["food_id"] == str(zone.id)
            assert state.model_result["subtipo"] == zone.subtipo

    def test_preserves_non_food_states_and_order(self) -> None:
        food_zones = self._food_zones()
        last_phase_id = UUID(PHASE_IDS["p3"])
        base = self._base_prediction(food_zones, last_phase_id)
        result = self._food_result(food_zones, last_phase_id)

        merged = merge_food_into_prediction(base, result)

        assert [zs.zone_id for zs in merged.zone_states] == [
            zs.zone_id for zs in base.zone_states
        ]
        other = merged.zone_states[-2]
        banos = merged.zone_states[-1]
        assert other.zone_id == self.OTHER_ID
        assert other.saturation_level == pytest.approx(0.10)
        assert other.model_result is None
        assert banos.zone_id == self.BANOS_ID
        assert banos.operational_state == "CRITICO"

    def test_preserves_timestamp_and_phase_ids(self) -> None:
        food_zones = self._food_zones()
        last_phase_id = UUID(PHASE_IDS["p3"])
        base = self._base_prediction(food_zones, last_phase_id)
        result = self._food_result(food_zones, last_phase_id)

        merged = merge_food_into_prediction(base, result)

        assert merged.timestamp == base.timestamp
        assert merged.active_phase_id == base.active_phase_id
        assert merged.active_event_day_phase_id == base.active_event_day_phase_id

    def test_none_result_returns_same_prediction(self) -> None:
        last_phase_id = UUID(PHASE_IDS["p3"])
        base = self._base_prediction((), last_phase_id)
        assert merge_food_into_prediction(base, None) is base

    def test_derive_uses_base_state_operational_fields(self) -> None:
        zone = Zone(
            id=UUID(FOOD_IDS["patio"]),
            name="Comida patio",
            zone_type_id=UUID(ZT_IDS["comida"]),
            capacity=400,
            type="comida",
            subtipo="patio_de_comidas",
            reference_point_distance=250.0,
        )
        base_state = ZoneState(
            zone_id=zone.id,
            operational_state="CONGESTIONADO",
            reasoning_factors=["alta demanda"],
            projected_density=320,
        )
        durations = {zone.id: 0.5}
        phase_state = FoodV1Model().simulate(
            self._phases(), [zone], MAX_PEOPLE, durations
        )[0]

        derived = derive_food_zone_state(zone, phase_state, base_state)

        assert derived.operational_state == "CONGESTIONADO"
        assert derived.reasoning_factors == ["alta demanda"]
        assert derived.projected_density == 320
        assert derived.type == "comida"
        assert derived.subtipo == "patio_de_comidas"
        assert derived.confidence is None
        assert derived.estimated_wait is None
        metrics = derived.model_result
        assert metrics is not None
        assert metrics["distance"] == pytest.approx(250.0)
        assert metrics["unabsorbed"] == pytest.approx(phase_state.unabsorbed)
