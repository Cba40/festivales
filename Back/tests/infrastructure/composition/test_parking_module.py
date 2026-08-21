"""ETAPA 3 Parking V1 — ParkingModule: ejecución de simulate() sobre el
universo físico real.

La infraestructura de BD se simula con AsyncMock (mismo patrón que el resto
de la suite): no se accede a base de datos alguna, no se usa BD local ni Neon.
Se verifica que ParkingV1Model recibe TODAS las zonas Parking, todas las fases,
los inputs de contexto y que simulate() se ejecuta con sus invariantes y
determinismo.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.domain.entities.event_day import EventDay
from src.domain.entities.zone import Zone
from src.domain.models.parking_v1_model import ParkingV1Model
from src.infrastructure.composition.parking_module import (
    ParkingModule,
    _load_parking_zones,
)

EVENT_ID = "event-parking-1"
DAY_ID = "11111111-1111-1111-1111-111111111111"
OP_ID = "22222222-2222-2222-2222-222222222222"
ATTENDANCE_ID = "55555555-5555-5555-5555-555555555555"
ZT_IDS = {
    "estacionamiento": "33333333-3333-3333-3333-333333333333",
    "transporte": "44444444-4444-4444-4444-444444444444",
    "comida": "55555555-5555-5555-5555-555555555556",
}

PARKING_IDS = {
    "A": "a0000000-0000-0000-0000-000000000001",
    "B": "a0000000-0000-0000-0000-000000000002",
    "C": "a0000000-0000-0000-0000-000000000003",
    "D": "a0000000-0000-0000-0000-000000000004",
    "F": "a0000000-0000-0000-0000-000000000005",
    "G": "a0000000-0000-0000-0000-000000000006",
}

NON_PARKING_IDS = {
    "transporte": "b0000000-0000-0000-0000-000000000001",
    "comida": "b0000000-0000-0000-0000-000000000002",
}

PHASE_IDS = {
    "p1": "c0000000-0000-0000-0000-000000000001",
    "p2": "c0000000-0000-0000-0000-000000000002",
    "p3": "c0000000-0000-0000-0000-000000000003",
}

REF_LAT = -31.4135
REF_LNG = -64.1811

# (id, capacity, available_capacity, latitude, longitude)
ZONE_SPECS = {
    "A": (500, 500, -31.4135, -64.1811),
    "B": (400, 300, -31.42, -64.19),
    "C": (300, 300, -31.43, -64.20),
    "D": (200, 200, -31.40, -64.17),
    "F": (250, 250, -31.415, -64.185),
    "G": (150, 0, -31.41, -64.18),
}

ESTIMATED_VEHICLES = 8000
AVERAGE_PARKING_DURATION = 4.0
DURATION_MIN = 240  # 4 h en minutos: mismo valor efectivo que AVERAGE_PARKING_DURATION
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


def _zone_row(zone_id, name, ztype, capacity, available_capacity, lat, lng):
    return SimpleNamespace(
        id=zone_id,
        name=name,
        type=ztype,
        subtipo=None,
        capacity=capacity,
        available_capacity=available_capacity,
        latitude=lat,
        longitude=lng,
    )


def _parking_zone_rows():
    rows = []
    for letter in ("A", "B", "C", "D", "F", "G"):
        capacity, available, lat, lng = ZONE_SPECS[letter]
        rows.append(
            _zone_row(
                PARKING_IDS[letter],
                f"Parking {letter}",
                "estacionamiento",
                capacity,
                available,
                lat,
                lng,
            )
        )
    return rows


def _non_parking_zone_rows():
    return [
        _zone_row(
            NON_PARKING_IDS["transporte"],
            "Parada Linea",
            "transporte",
            300,
            300,
            -31.4135,
            -64.1811,
        ),
        _zone_row(
            NON_PARKING_IDS["comida"],
            "Patio Comida",
            "comida",
            200,
            200,
            -31.42,
            -64.19,
        ),
    ]


def _ed_row(
    estimated_vehicles=ESTIMATED_VEHICLES,
    average_parking_duration=AVERAGE_PARKING_DURATION,
):
    return SimpleNamespace(
        id=DAY_ID,
        date=date(2026, 7, 15),
        attendance_level_id=ATTENDANCE_ID,
        operational_profile_id=UUID("99999999-0000-0000-0000-000000000001"),
        operational_start_min=600,
        operational_end_min=960,
        estimated_vehicles=estimated_vehicles,
        average_parking_duration=average_parking_duration,
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


def _mock_session(zone_rows, ed_row, config_override=None, config_default=None):
    session = AsyncMock()
    captured_stmts = []
    zone_type_rows = [
        SimpleNamespace(slug="estacionamiento", id=ZT_IDS["estacionamiento"]),
        SimpleNamespace(slug="transporte", id=ZT_IDS["transporte"]),
        SimpleNamespace(slug="comida", id=ZT_IDS["comida"]),
    ]
    ref_row = SimpleNamespace(
        reference_point_latitude=REF_LAT,
        reference_point_longitude=REF_LNG,
    )
    execute_calls = [
        _scalars_result(zone_type_rows),
        _one_result(ref_row),
        _scalars_result(zone_rows),
        _scalar_one_result(ed_row),
        # Permanencia Parking V1: service_configs (override por jornada;
        # default global solo se consulta si el override no existió).
        _scalar_one_result(config_override),
    ]
    if config_override is None:
        execute_calls.append(_scalar_one_result(config_default))
    original = AsyncMock(side_effect=execute_calls)

    async def fake_execute(stmt, *args, **kwargs):
        captured_stmts.append(stmt)
        return await original(stmt, *args, **kwargs)

    session.execute = fake_execute
    session.captured_stmts = captured_stmts
    return session


def _expected_parking_ids():
    return {UUID(PARKING_IDS[letter]) for letter in ("A", "B", "C", "D", "F", "G")}


def _total_capacity():
    return sum(ZONE_SPECS[letter][0] for letter in ("A", "B", "C", "D", "F", "G"))


class TestParkingModuleDataFlow:
    async def test_all_parking_zones_delivered(self) -> None:
        session = _mock_session(_parking_zone_rows(), _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )

        assert result is not None
        assert len(result.parking_zones) == 6
        assert {zone.id for zone in result.parking_zones} == _expected_parking_ids()

    async def test_non_parking_zones_excluded_from_module(self) -> None:
        rows = _parking_zone_rows() + _non_parking_zone_rows()
        session = _mock_session(rows, _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )

        assert result is not None
        assert len(result.parking_zones) == 6
        delivered = {zone.id for zone in result.parking_zones}
        assert delivered == _expected_parking_ids()
        assert not delivered.intersection({UUID(v) for v in NON_PARKING_IDS.values()})

    async def test_zones_query_filters_by_type_estacionamiento(self) -> None:
        rows = _parking_zone_rows() + _non_parking_zone_rows()
        session = _mock_session(rows, _ed_row())
        await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )

        zones_stmt = session.captured_stmts[2]
        sql = str(zones_stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "estacionamiento" in sql
        assert "zones.type" in sql

    async def test_each_zone_preserves_physical_fields(self) -> None:
        session = _mock_session(_parking_zone_rows(), _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None

        by_id = {zone.id: zone for zone in result.parking_zones}
        for letter in ("A", "B", "C", "D", "F", "G"):
            zone = by_id[UUID(PARKING_IDS[letter])]
            capacity, available, lat, lng = ZONE_SPECS[letter]
            assert zone.capacity == capacity
            assert zone.available_capacity == available
            assert zone.latitude == lat
            assert zone.longitude == lng
            assert zone.type == "estacionamiento"

    async def test_reference_point_distance_computed_per_zone(self) -> None:
        session = _mock_session(_parking_zone_rows(), _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None

        distances = {
            zone.id: zone.reference_point_distance for zone in result.parking_zones
        }
        zone_a = UUID(PARKING_IDS["A"])
        assert distances[zone_a] == 0.0
        for zone in result.parking_zones:
            assert zone.reference_point_distance is not None
            assert zone.reference_point_distance >= 0.0

    async def test_full_phase_sequence_delivered(self) -> None:
        session = _mock_session(_parking_zone_rows(), _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None

        assert len(result.phases) == 3
        assert [p.start_min for p in result.phases] == [600, 720, 840]
        assert [p.end_min for p in result.phases] == [720, 840, 960]
        assert [p.intensity for p in result.phases] == [0.25, 0.50, 0.75]

    async def test_estimated_vehicles_arrives(self) -> None:
        session = _mock_session(_parking_zone_rows(), _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.estimated_vehicles == ESTIMATED_VEHICLES

    async def test_average_parking_duration_arrives(self) -> None:
        session = _mock_session(_parking_zone_rows(), _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.average_parking_duration == AVERAGE_PARKING_DURATION


class TestParkingModuleSimulation:
    async def test_simulate_executes_multiple_zones_and_phases(self) -> None:
        session = _mock_session(_parking_zone_rows(), _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert len(result.phase_results) == 3
        assert [phase.index for phase in result.phase_results] == [1, 2, 3]

    async def test_each_parking_zone_has_result_in_every_phase(self) -> None:
        session = _mock_session(_parking_zone_rows(), _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None

        expected = _expected_parking_ids()
        for phase in result.phase_results:
            assert set(phase.occupied.keys()) == expected

    async def test_available_capacity_delivered_to_zone_entity(self) -> None:
        session = _mock_session(_parking_zone_rows(), _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        by_id = {zone.id: zone for zone in result.parking_zones}
        assert by_id[UUID(PARKING_IDS["B"])].available_capacity == 300
        assert by_id[UUID(PARKING_IDS["G"])].available_capacity == 0
        assert by_id[UUID(PARKING_IDS["A"])].available_capacity == 500

    async def test_initial_occupied_is_zero_regardless_of_available(self) -> None:
        session = _mock_session(_parking_zone_rows(), _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        initial = ParkingV1Model().initial_occupied(result.parking_zones)
        for zone in result.parking_zones:
            assert initial[zone.id] == pytest.approx(0.0)
        assert sum(initial.values()) == pytest.approx(0.0)

    async def test_first_phase_starts_from_zero(self) -> None:
        session = _mock_session(_parking_zone_rows(), _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        first = result.phase_results[0]
        assert first.remain == pytest.approx(0.0, abs=1e-9)
        assert first.stock == pytest.approx(
            min(first.v_expected, _total_capacity()), abs=1e-6
        )
        assert first.occupied[UUID(PARKING_IDS["G"])] >= 0.0

    async def test_invariants(self) -> None:
        session = _mock_session(_parking_zone_rows(), _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None

        capacities = {
            zone.id: zone.capacity for zone in result.parking_zones
        }
        total_capacity = _total_capacity()
        initial_occupied = ParkingV1Model().initial_occupied(result.parking_zones)
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
            r = math.exp(-delta_hours / AVERAGE_PARKING_DURATION)
            assert phase.remain == pytest.approx(prev_stock * r)
            prev_stock = phase.stock

    async def test_determinism(self) -> None:
        session_a = _mock_session(_parking_zone_rows(), _ed_row())
        session_b = _mock_session(_parking_zone_rows(), _ed_row())
        result_a = await ParkingModule(session_a).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        result_b = await ParkingModule(session_b).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result_a is not None
        assert result_b is not None

        assert result_a.parking_zones == result_b.parking_zones
        assert result_a.phases == result_b.phases
        assert result_a.phase_results == result_b.phase_results


class TestParkingModuleEdges:
    async def test_no_parking_zones_returns_none(self) -> None:
        session = _mock_session(_non_parking_zone_rows(), _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is None

    async def test_no_event_day_returns_none(self) -> None:
        session = _mock_session(_parking_zone_rows(), None)
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is None

    async def test_missing_estimated_vehicles_raises(self) -> None:
        session = _mock_session(
            _parking_zone_rows(), _ed_row(estimated_vehicles=None)
        )
        with pytest.raises(ValueError):
            await ParkingModule(session).execute(
                timestamp=TIMESTAMP,
                event_id=EVENT_ID,
            )

    async def test_missing_duration_raises(self) -> None:
        session = _mock_session(
            _parking_zone_rows(), _ed_row(average_parking_duration=None)
        )
        with pytest.raises(ValueError):
            await ParkingModule(session).execute(
                timestamp=TIMESTAMP,
                event_id=EVENT_ID,
            )


class TestParkingModuleDurationResolution:
    async def test_service_config_override_takes_precedence(self) -> None:
        session = _mock_session(
            _parking_zone_rows(),
            _ed_row(),
            config_override=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.average_parking_duration == DURATION_MIN / 60.0
        assert result.duration_source == "service_config"

    async def test_service_config_falls_back_to_default_global(self) -> None:
        session = _mock_session(
            _parking_zone_rows(),
            _ed_row(),
            config_default=SimpleNamespace(average_duration_min=DURATION_MIN),
        )
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.average_parking_duration == DURATION_MIN / 60.0
        assert result.duration_source == "service_config"

    async def test_falls_back_to_event_day_duration_without_config(self) -> None:
        session = _mock_session(_parking_zone_rows(), _ed_row())
        result = await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )
        assert result is not None
        assert result.average_parking_duration == AVERAGE_PARKING_DURATION
        assert result.duration_source == "event_day"

    async def test_service_config_query_uses_empty_subtipo(self) -> None:
        session = _mock_session(_parking_zone_rows(), _ed_row())
        await ParkingModule(session).execute(
            timestamp=TIMESTAMP,
            event_id=EVENT_ID,
        )

        config_sqls = [
            str(stmt.compile(compile_kwargs={"literal_binds": True}))
            for stmt in session.captured_stmts
            if "service_configs" in str(stmt)
        ]
        assert len(config_sqls) >= 1
        assert "coalesce(service_configs.subtipo, '') = ''" in config_sqls[0]
        assert "service_configs.event_day_id" in config_sqls[0]


class TestLoadParkingZones:
    async def test_filters_to_parking_only(self) -> None:
        session = AsyncMock()
        rows = _parking_zone_rows() + _non_parking_zone_rows()
        session.execute = AsyncMock(return_value=_scalars_result(rows))

        zones = await _load_parking_zones(
            session,
            EVENT_ID,
            {slug: UUID(zt_id) for slug, zt_id in ZT_IDS.items()},
            REF_LAT,
            REF_LNG,
        )

        assert len(zones) == 6
        assert {zone.id for zone in zones} == _expected_parking_ids()
        for zone in zones:
            assert isinstance(zone, Zone)
            assert zone.capacity > 0
            assert zone.latitude is not None
            assert zone.longitude is not None