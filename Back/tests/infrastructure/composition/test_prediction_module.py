"""Etapa 1 Parking V1 — flujo de PredictionModule y corrección de
attendance_level_id (varchar -> UUID) en la frontera ORM -> dominio.

El error 500 de producción se originaba aquí: la columna legacy
event_days.attendance_level_id es varchar(36) y EventDay exige UUID.

Toda la infraestructura de BD se simula con AsyncMock (mismo patrón que el
resto de la suite): no se accede a base de datos alguna.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.domain.entities.zone import Zone
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.infrastructure.composition.prediction_module import (
    PredictionModule,
    _to_uuid_or_none,
)

EVENT_ID = "event-1"
DAY_IDS = {
    "id": "11111111-1111-1111-1111-111111111111",
}
ZT_IDS = {
    "estacionamiento": "22222222-2222-2222-2222-222222222222",
    "comida": "33333333-3333-3333-3333-333333333333",
}
PHASE_ID = "44444444-4444-4444-4444-444444444444"
ATTENDANCE_ID = "55555555-5555-5555-5555-555555555555"
ZONE_IDS = {
    "norte": "66666666-6666-6666-6666-666666666601",
    "sur": "66666666-6666-6666-6666-666666666602",
}

REF_LAT = -31.4135
REF_LNG = -64.1811

ZONE_NORTE_LAT = -31.4135
ZONE_NORTE_LNG = -64.1811
ZONE_SUR_LAT = -31.42
ZONE_SUR_LNG = -64.19


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


class CapturingEngine:
    """Reemplaza ContextEngine para capturar los datos que llegan al dominio."""

    def __init__(self) -> None:
        self.captured_event_day = None
        self.captured_zones: list[Zone] = []

    def predict(
        self,
        *,
        timestamp: datetime,
        zones,
        zone_behaviors,
        operational_phases,
        attendance_level,
        event_day,
        events,
    ) -> TerritorialPrediction:
        self.captured_event_day = event_day
        self.captured_zones = list(zones)
        return TerritorialPrediction(
            timestamp=timestamp,
            zone_states=[
                ZoneState(
                    zone_id=zone.id,
                    operational_state="NORMAL",
                    active_restriction=None,
                    type=zone.type,
                    subtipo=zone.subtipo,
                )
                for zone in zones
            ],
            active_phase_id=UUID(PHASE_ID),
            active_event_day_phase_id=UUID("77777777-7777-7777-7777-777777777777"),
        )


def _mock_full_flow_session(
    attendance_level_id: str | None = ATTENDANCE_ID,
) -> AsyncMock:
    session = AsyncMock()

    zone_type_rows = [
        SimpleNamespace(slug="estacionamiento", id=ZT_IDS["estacionamiento"]),
        SimpleNamespace(slug="comida", id=ZT_IDS["comida"]),
    ]
    ref_row = SimpleNamespace(
        reference_point_latitude=REF_LAT,
        reference_point_longitude=REF_LNG,
    )
    zone_rows = [
        SimpleNamespace(
            id=ZONE_IDS["norte"],
            name="Parking Norte",
            type="estacionamiento",
            subtipo=None,
            capacity=500,
            latitude=ZONE_NORTE_LAT,
            longitude=ZONE_NORTE_LNG,
        ),
        SimpleNamespace(
            id=ZONE_IDS["sur"],
            name="Parking Sur",
            type="estacionamiento",
            subtipo=None,
            capacity=400,
            latitude=ZONE_SUR_LAT,
            longitude=ZONE_SUR_LNG,
        ),
    ]
    behavior_rows = [
        SimpleNamespace(
            id="88888888-8888-8888-8888-888888888888",
            zone_type_id=ZT_IDS["estacionamiento"],
            operational_phase_id=PHASE_ID,
            density_factor=0.8,
            flow_restriction="OPEN",
        ),
    ]
    ed_row = SimpleNamespace(
        id=DAY_IDS["id"],
        date=date(2026, 7, 15),
        attendance_level_id=attendance_level_id,
        operational_profile_id=UUID("99999999-0000-0000-0000-000000000001"),
        operational_start_min=0,
        operational_end_min=1440,
        estimated_vehicles=2500,
        average_parking_duration=4.0,
        phases=[
            SimpleNamespace(
                id="77777777-7777-7777-7777-777777777777",
                operational_phase_id=PHASE_ID,
                start_min=0,
                end_min=1440,
                intensity=0.5,
            )
        ],
    )
    attendance_row = SimpleNamespace(
        id=ATTENDANCE_ID,
        event_id=EVENT_ID,
        name="Normal",
        min_people=10000,
        max_people=25000,
    )
    phase_rows = [
        SimpleNamespace(
            id=PHASE_ID,
            name="Peak",
            sort_order=2,
        )
    ]

    execute_calls = [
        _scalars_result(zone_type_rows),
        _one_result(ref_row),
        _scalars_result(zone_rows),
        _scalars_result(behavior_rows),
        _scalar_one_result(ed_row),
    ]
    if attendance_level_id is not None:
        execute_calls.append(_scalar_one_result(attendance_row))
    execute_calls.append(_scalars_result(phase_rows))
    # operational_events (OperationalEventAdapter): sin eventos activos.
    execute_calls.append(_scalars_result([]))

    session.execute = AsyncMock(side_effect=execute_calls)
    return session


class TestAttendanceLevelIdConversion:
    """Conversión ORM -> dominio de attendance_level_id (varchar a UUID)."""

    def test_valid_string_uuid_is_converted(self) -> None:
        assert _to_uuid_or_none(ATTENDANCE_ID) == UUID(ATTENDANCE_ID)

    def test_none_stays_none(self) -> None:
        assert _to_uuid_or_none(None) is None

    def test_already_uuid_is_passed_through(self) -> None:
        assert _to_uuid_or_none(UUID(ATTENDANCE_ID)) == UUID(ATTENDANCE_ID)

    def test_invalid_string_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            _to_uuid_or_none("not-a-uuid")


class TestPredictionModuleFullFlow:
    async def test_execute_converts_attendance_level_id_from_varchar(self) -> None:
        engine = CapturingEngine()
        with patch(
            "src.infrastructure.composition.prediction_module.ContextEngine",
            return_value=engine,
        ):
            module = PredictionModule(_mock_full_flow_session())
            prediction = await module.execute(
                timestamp=datetime(2026, 7, 15, 15, 0, tzinfo=timezone.utc),
                event_id=EVENT_ID,
            )

        assert prediction is not None

        assert engine.captured_event_day is not None
        assert engine.captured_event_day.attendance_level_id == UUID(ATTENDANCE_ID)
        assert engine.captured_event_day.estimated_vehicles == 2500
        assert engine.captured_event_day.average_parking_duration == 4.0

        assert len(engine.captured_zones) == 2
        distances = {
            zone.id: zone.reference_point_distance
            for zone in engine.captured_zones
        }
        assert distances[UUID(ZONE_IDS["norte"])] == 0.0
        assert distances[UUID(ZONE_IDS["sur"])] is not None
        assert distances[UUID(ZONE_IDS["sur"])] > 0.0

    async def test_execute_accepts_none_attendance_level_id(self) -> None:
        engine = CapturingEngine()
        with patch(
            "src.infrastructure.composition.prediction_module.ContextEngine",
            return_value=engine,
        ):
            module = PredictionModule(_mock_full_flow_session(attendance_level_id=None))
            prediction = await module.execute(
                timestamp=datetime(2026, 7, 15, 15, 0, tzinfo=timezone.utc),
                event_id=EVENT_ID,
            )

        assert prediction is not None
        assert engine.captured_event_day is not None
        assert engine.captured_event_day.attendance_level_id is None
