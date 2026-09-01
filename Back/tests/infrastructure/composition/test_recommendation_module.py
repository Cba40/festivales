"""Etapa 1 Parking V1 — flujo de RecommendationModule.

Verifica que el flujo de recomendación transporta los inputs de Parking V1
(estimated_vehicles, average_parking_duration) y que reference_point_distance
queda disponible en las Zone del mismo modo que en el flujo de Prediction.

Toda la infraestructura de BD se simula con AsyncMock (mismo patrón que el
resto de la suite): no se accede a base de datos alguna.
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest

from src.domain.entities.zone import Zone
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import ActionType, RequestedAction
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.infrastructure.composition.recommendation_module import (
    RecommendationModule,
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


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[None] * 8)
    return session


def _mock_full_flow_session() -> AsyncMock:
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
            available_capacity=500,
            latitude=ZONE_NORTE_LAT,
            longitude=ZONE_NORTE_LNG,
        ),
        SimpleNamespace(
            id=ZONE_IDS["sur"],
            name="Parking Sur",
            type="estacionamiento",
            subtipo=None,
            capacity=400,
            available_capacity=400,
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
        date=datetime(2026, 7, 15, 15, 0).date(),
        attendance_level_id=ATTENDANCE_ID,
        operational_profile_id=UUID("99999999-0000-0000-0000-000000000001"),
        operational_start_min=840,
        operational_end_min=1080,
        estimated_vehicles=2500,
        average_parking_duration=4.0,
        phases=[
            SimpleNamespace(
                id="77777777-7777-7777-7777-777777777777",
                operational_phase_id=PHASE_ID,
                start_min=840,
                end_min=1080,
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

    session.execute = AsyncMock(
        side_effect=[
            _scalars_result(zone_type_rows),
            _one_result(ref_row),
            _scalars_result(zone_rows),
            _scalars_result(behavior_rows),
            _scalar_one_result(ed_row),
            _scalar_one_result(attendance_row),
            _scalars_result(phase_rows),
            # operational_events (OperationalEventAdapter): sin eventos activos.
            _scalars_result([]),
            # ETAPA 4 — queries adicionales de ParkingModule (puente Parking):
            _scalars_result(zone_type_rows),
            _one_result(ref_row),
            _scalars_result(zone_rows),
            _scalar_one_result(ed_row),
            # Permanencia Parking V1: service_configs override + default
            # (sin filas → fallback a EventDay.average_parking_duration).
            _scalar_one_result(None),
            _scalar_one_result(None),
        ]
    )
    return session


def _user_context() -> UserContext:
    return UserContext(
        user_id=UUID("99999999-9999-9999-9999-999999999999"),
        access_level=AccessLevel.STANDARD,
    )


def _mobility_context() -> MobilityContext:
    return MobilityContext(
        current_zone_id=None,
        speed=1.5,
        accessibility_required=False,
    )


def _requested_action() -> RequestedAction:
    return RequestedAction(action_type=ActionType.SEEK_PARKING)


class TestRecommendationModuleZonesSpatialData:
    async def test_zones_receive_reference_point_distance(self, mock_session) -> None:
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
        mock_session.execute.side_effect = [_scalars_result(zone_rows)]

        from src.infrastructure.composition.recommendation_module import _load_zones

        type_map = {"estacionamiento": UUID(ZT_IDS["estacionamiento"])}
        zones = await _load_zones(
            mock_session,
            EVENT_ID,
            type_map,
            ref_lat=REF_LAT,
            ref_lng=REF_LNG,
        )

        assert len(zones) == 2
        by_name = {z.name: z for z in zones}

        norte = by_name["Parking Norte"]
        sur = by_name["Parking Sur"]

        assert norte.latitude == ZONE_NORTE_LAT
        assert norte.longitude == ZONE_NORTE_LNG
        assert norte.reference_point_distance == 0.0

        assert sur.latitude == ZONE_SUR_LAT
        assert sur.longitude == ZONE_SUR_LNG
        assert sur.reference_point_distance is not None
        assert sur.reference_point_distance > 0.0

    async def test_zones_without_reference_point_keep_distance_none(self, mock_session) -> None:
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
        ]
        mock_session.execute.side_effect = [_scalars_result(zone_rows)]

        from src.infrastructure.composition.recommendation_module import _load_zones

        type_map = {"estacionamiento": UUID(ZT_IDS["estacionamiento"])}
        zones = await _load_zones(
            mock_session,
            EVENT_ID,
            type_map,
            ref_lat=None,
            ref_lng=None,
        )

        assert len(zones) == 1
        assert zones[0].reference_point_distance is None


class TestRecommendationModuleFullFlow:
    async def test_execute_transports_parking_inputs_and_distance(self) -> None:
        engine = CapturingEngine()
        with patch(
            "src.infrastructure.composition.recommendation_module.ContextEngine",
            return_value=engine,
        ):
            module = RecommendationModule(_mock_full_flow_session())
            recommendations, prediction = await module.execute(
                timestamp=datetime(2026, 7, 15, 15, 0),
                event_id=EVENT_ID,
                user_context=_user_context(),
                mobility_context=_mobility_context(),
                requested_action=_requested_action(),
                limit=5,
            )

        assert prediction is not None
        assert isinstance(recommendations, list)
        assert all(isinstance(r, ZoneRecommendation) for r in recommendations)

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