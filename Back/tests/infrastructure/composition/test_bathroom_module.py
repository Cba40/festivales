"""ETAPA 3 Baños V1 — BathroomModule: ejecución de simulate() sobre el
universo físico real.

La infraestructura de BD se simula con AsyncMock (mismo patrón que el resto
de la suite): no se accede a base de datos alguna, no se usa BD local ni Neon.
Se verifica que BathroomV1Model recibe TODAS las zonas de servicios/baños,
todas las fases, max_people (AttendanceLevel), la permanencia resuelta desde
ServiceConfig (override → default, en MINUTOS, convertida a horas) y que
simulate() se ejecuta con sus invariantes y determinismo.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.domain.entities.zone import Zone
from src.domain.models.bathroom_v1_model import BathroomV1Model
from src.infrastructure.composition.bathroom_module import (
    BathroomModule,
    _load_bathroom_zones,
)

EVENT_ID = "event-bathroom-1"
DAY_ID = "11111111-1111-1111-1111-111111111111"
OP_ID = "22222222-2222-2222-2222-222222222222"
ATTENDANCE_ID = "55555555-5555-5555-5555-555555555555"
ZT_IDS = {
    "servicios": "33333333-3333-3333-3333-333333333333",
    "transporte": "44444444-4444-4444-4444-444444444444",
    "comida": "55555555-5555-5555-5555-555555555556",
}

BATHROOM_IDS = {
    "A": "a0000000-0000-0000-0000-000000000001",
    "B": "a0000000-0000-0000-0000-000000000002",
    "C": "a0000000-0000-0000-0000-000000000003",
    "D": "a0000000-0000-0000-0000-000000000004",
    "F": "a0000000-0000-0000-0000-000000000005",
    "G": "a0000000-0000-0000-0000-000000000006",
}

NON_BATHROOM_IDS = {
    "transporte": "b0000000-0000-0000-0000-000000000001",
    "comida": "b0000000-0000-0000-0000-000000000002",
    "hidratacion": "b0000000-0000-0000-0000-000000000003",
}

PHASE_IDS = {
    "p1": "c0000000-0000-0000-0000-000000000001",
    "p2": "c0000000-0000-0000-0000-000000000002",
    "p3": "c0000000-0000-0000-0000-000000000003",
}

REF_LAT = -31.4135
REF_LNG = -64.1811

# (capacity, available_capacity, latitude, longitude)
ZONE_SPECS = {
    "A": (500, 500, -31.4135, -64.1811),
    "B": (400, 300, -31.42, -64.19),
    "C": (300, 300, -31.43, -64.20),
    "D": (200, 200, -31.40, -64.17),
    "F": (250, 250, -31.415, -64.185),
    "G": (150, 0, -31.41, -64.18),
}

MAX_PEOPLE = 25000
DURATION_MIN = 5
DEFAULT_DURATION_MIN = 8
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


def _bathroom_zone_rows():
    rows = []
    for letter in ("A", "B", "C", "D", "F", "G"):
        capacity, available, lat, lng = ZONE_SPECS[letter]
        rows.append(
            _zone_row(
                BATHROOM_IDS[letter],
                f"Banos {letter}",
                "servicios",
                "banos",
                capacity,
                available,
                lat,
                lng,
            )
        )
    return rows


def _non_bathroom_zone_rows():
    return [
        _zone_row(
            NON_BATHROOM_IDS["transporte"],
            "Parada Linea",
            "transporte",
            None,
            300,
            300,
            -31.4135,
            -64.1811,
        ),
        _zone_row(
            NON_BATHROOM_IDS["comida"],
            "Patio Comida",
            "comida",
            None,
            200,
            200,
            -31.42,
            -64.19,
        ),
        _zone_row(
            NON_BATHROOM_IDS["hidratacion"],
            "Fuente Agua",
            "servicios",
            "hidratacion",
            150,
            150,
            -31.43,
            -64.20,
        ),
    ]


def _ed_row():
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
            for phase_id, start_min, end_min, intensity in PHASES_SPEC
        ],
    )


def _attendance_row(max_people=MAX_PEOPLE):
    return SimpleNamespace(
        id=ATTENDANCE_ID,
        event_id=EVENT_ID,
        name="Normal",
        min_people=10000,
        max_people=max_people,
    )


def _mock_session(
    zone_rows,
    ed_row,
    *,
    attendance_row=None,
    override_row=None,
    default_row=None,
):
    """Mock de sesión con despacho por tabla (SQL).

    `resolve_active_event_day` consulta event_days dos veces (hoy y ayer):
    ambas devuelven `ed_row`. El despacho por tabla evita la colisión posicional
    entre la segunda consulta de event_days y la carga de attendance_levels.
    """
    session = AsyncMock()
    captured_stmts = []
    zone_type_rows = [
        SimpleNamespace(slug="servicios", id=ZT_IDS["servicios"]),
        SimpleNamespace(slug="transporte", id=ZT_IDS["transporte"]),
        SimpleNamespace(slug="comida", id=ZT_IDS["comida"]),
    ]
    ref_row = SimpleNamespace(
        reference_point_latitude=REF_LAT,
        reference_point_longitude=REF_LNG,
    )
    service_config_calls = {"count": 0}

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
            n = service_config_calls["count"]
            service_config_calls["count"] += 1
            row = override_row if n == 0 else default_row
            return _scalar_one_result(row)
        raise AssertionError(f"unexpected statement: {sql}")

    session.execute = fake_execute
    session.captured_stmts = captured_stmts
    return session


def _expected_bathroom_ids():
    return {UUID(BATHROOM_IDS[letter]) for letter in ("A", "B", "C", "D", "F", "G")}


def _total_capacity():
    return sum(ZONE_SPECS[letter][0] for letter in ("A", "B", "C", "D", "F", "G"))


def _duration_hours():
    return DURATION_MIN / 60.0


class TestBathroomModuleDataFlow:
    async def test_all_bathroom_zones_delivered(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )

        assert result is not None
        assert len(result.bathroom_zones) == 6
        assert {zone.id for zone in result.bathroom_zones} == _expected_bathroom_ids()

    async def test_non_bathroom_zones_excluded_from_module(self) -> None:
        rows = _bathroom_zone_rows() + _non_bathroom_zone_rows()
        session = _mock_session(
            rows,
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )

        assert result is not None
        assert len(result.bathroom_zones) == 6
        delivered = {zone.id for zone in result.bathroom_zones}
        assert delivered == _expected_bathroom_ids()
        assert not delivered.intersection({UUID(v) for v in NON_BATHROOM_IDS.values()})

    async def test_zones_query_filters_by_servicios_y_banos(self) -> None:
        rows = _bathroom_zone_rows() + _non_bathroom_zone_rows()
        session = _mock_session(
            rows,
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )

        zones_stmt = session.captured_stmts[2]
        sql = str(zones_stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "servicios" in sql
        assert "banos" in sql
        assert "zones.type" in sql
        assert "zones.subtipo" in sql

    async def test_each_zone_preserves_physical_fields(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None

        by_id = {zone.id: zone for zone in result.bathroom_zones}
        for letter in ("A", "B", "C", "D", "F", "G"):
            zone = by_id[UUID(BATHROOM_IDS[letter])]
            capacity, available, lat, lng = ZONE_SPECS[letter]
            assert zone.capacity == capacity
            assert zone.available_capacity == available
            assert zone.latitude == lat
            assert zone.longitude == lng
            assert zone.type == "servicios"
            assert zone.subtipo == "banos"

    async def test_reference_point_distance_computed_per_zone(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None

        distances = {
            zone.id: zone.reference_point_distance for zone in result.bathroom_zones
        }
        zone_a = UUID(BATHROOM_IDS["A"])
        assert distances[zone_a] == 0.0
        for zone in result.bathroom_zones:
            assert zone.reference_point_distance is not None
            assert zone.reference_point_distance >= 0.0

    async def test_full_phase_sequence_delivered(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
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
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.max_people == MAX_PEOPLE

    async def test_average_duration_min_arrives(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.average_duration_min == DURATION_MIN

    async def test_duration_converted_min_to_hours(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.duration_hours == pytest.approx(_duration_hours())

    async def test_service_config_override_takes_precedence_over_default(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
            default_row=SimpleNamespace(average_duration_min=DEFAULT_DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.average_duration_min == DURATION_MIN

    async def test_service_config_falls_back_to_default(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=None,
            default_row=SimpleNamespace(average_duration_min=DEFAULT_DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.average_duration_min == DEFAULT_DURATION_MIN


class TestBathroomModuleSimulation:
    async def test_simulate_executes_multiple_zones_and_phases(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert len(result.phase_results) == 3
        assert [phase.index for phase in result.phase_results] == [1, 2, 3]

    async def test_each_bathroom_zone_has_result_in_every_phase(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None

        expected = _expected_bathroom_ids()
        for phase in result.phase_results:
            assert set(phase.occupied.keys()) == expected

    async def test_initial_occupied_is_zero(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        initial = BathroomV1Model().initial_occupied(result.bathroom_zones)
        for zone in result.bathroom_zones:
            assert initial[zone.id] == pytest.approx(0.0)
        assert sum(initial.values()) == pytest.approx(0.0)

    async def test_first_phase_starts_from_zero(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        first = result.phase_results[0]
        assert first.remain == pytest.approx(0.0, abs=1e-9)
        assert first.stock == pytest.approx(
            min(first.v_expected, _total_capacity()), abs=1e-6
        )
        assert first.occupied[UUID(BATHROOM_IDS["G"])] >= 0.0

    async def test_invariants(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None

        capacities = {
            zone.id: zone.capacity for zone in result.bathroom_zones
        }
        total_capacity = _total_capacity()
        duration_hours = _duration_hours()
        initial_occupied = BathroomV1Model().initial_occupied(result.bathroom_zones)
        prev_stock = sum(initial_occupied.values())
        assert prev_stock == pytest.approx(0.0)
        for phase in result.phase_results:
            occupied_sum = sum(phase.occupied.values())
            assert occupied_sum == pytest.approx(phase.stock)
            assert phase.stock <= total_capacity
            assert phase.unabsorbed == pytest.approx(
                max(0.0, phase.v_expected - phase.entries)
            )
            for zone_id, occupied in phase.occupied.items():
                assert 0.0 <= occupied <= capacities[zone_id]
            delta_hours = (PHASES_SPEC[phase.index - 1][2] - PHASES_SPEC[phase.index - 1][1]) / 60.0
            r = math.exp(-delta_hours / duration_hours)
            assert phase.remain == pytest.approx(prev_stock * r)
            prev_stock = phase.stock

    async def test_determinism(self) -> None:
        session_a = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        session_b = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result_a = await BathroomModule(session_a).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        result_b = await BathroomModule(session_b).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result_a is not None
        assert result_b is not None

        assert result_a.bathroom_zones == result_b.bathroom_zones
        assert result_a.phases == result_b.phases
        assert result_a.phase_results == result_b.phase_results


class TestBathroomModuleEdges:
    async def test_no_bathroom_zones_returns_none(self) -> None:
        session = _mock_session(_non_bathroom_zone_rows(), _ed_row())
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is None

    async def test_no_event_day_returns_none(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            None,
            attendance_row=_attendance_row(),
        )
        result = await BathroomModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is None

    async def test_missing_max_people_raises(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(max_people=None),
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        with pytest.raises(ValueError):
            await BathroomModule(session).execute(
                timestamp=TIMESTAMP,
                event_id=EVENT_ID,
            )

    async def test_missing_attendance_level_raises(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=None,
            override_row=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        with pytest.raises(ValueError):
            await BathroomModule(session).execute(
                timestamp=TIMESTAMP,
                event_id=EVENT_ID,
            )

    async def test_missing_service_config_raises(self) -> None:
        session = _mock_session(
            _bathroom_zone_rows(),
            _ed_row(),
            attendance_row=_attendance_row(),
            override_row=None,
            default_row=None,
        )
        with pytest.raises(ValueError):
            await BathroomModule(session).execute(
                timestamp=TIMESTAMP,
                event_id=EVENT_ID,
            )


class TestLoadBathroomZones:
    async def test_filters_to_bathroom_only(self) -> None:
        session = AsyncMock()
        rows = _bathroom_zone_rows() + _non_bathroom_zone_rows()
        session.execute = AsyncMock(return_value=_scalars_result(rows))

        zones = await _load_bathroom_zones(
            session,
            EVENT_ID,
            {slug: UUID(zt_id) for slug, zt_id in ZT_IDS.items()},
            REF_LAT,
            REF_LNG,
        )

        assert len(zones) == 6
        assert {zone.id for zone in zones} == _expected_bathroom_ids()
        for zone in zones:
            assert isinstance(zone, Zone)
            assert zone.type == "servicios"
            assert zone.subtipo == "banos"
            assert zone.capacity > 0
            assert zone.latitude is not None
            assert zone.longitude is not None