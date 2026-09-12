"""Etapa 1 Learning & Analytics — MetricService unit tests.

Las fixtures replican el esquema/conteos confirmados de Neon (110
predicciones, 2 observaciones de agosto 2026, 2 operational_events y 110
zone_behaviors) y usan el mismo patron de la suite: AsyncSession simulada,
sin acceso a base de datos.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from app.models.operational_event import OperationalEvent
from app.models.zone import Zone
from app.models.zone_type import ZoneType
from src.application.learning.metric_service import MetricService
from src.domain.entities.zone_behavior import FlowRestriction
from src.infrastructure.persistence.models import (
    OperationalObservationModel,
    PredictionModel,
    ZoneBehaviorModel,
)
from src.infrastructure.persistence.repositories.prediction_repository import (
    SQLPredictionRepository,
)

DAY = "11111111-1111-1111-1111-111111111111"
PHASE = "22222222-2222-2222-2222-222222222222"
EVENT_DAY_PHASE = "77777777-7777-7777-7777-777777777777"
ZONE_A = "33333333-3333-3333-3333-333333333301"
ZONE_B = "33333333-3333-3333-3333-333333333302"
ZT_A = "44444444-4444-4444-4444-444444444401"
ZT_B = "44444444-4444-4444-4444-444444444402"
EVENT = "event-1"
UNAFFECTED_PHASE = "55555555-5555-5555-5555-555555555555"

T_09_00 = datetime(2026, 8, 1, 9, 0, 0)
T_09_10 = datetime(2026, 8, 1, 9, 10, 0)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _ScalarsResult:
    def __init__(self, rows: list) -> None:
        self._rows = list(rows)

    def all(self) -> list:
        return self._rows


class _Result:
    def __init__(self, rows: list) -> None:
        self._rows = list(rows)

    def scalars(self) -> _ScalarsResult:
        return _ScalarsResult(self._rows)


class FakeSession:
    """AsyncSession simulada que enruta cada SELECT por nombre de tabla."""

    def __init__(self, tables: dict[str, list]) -> None:
        self._tables = tables

    async def execute(self, stmt):
        compiled = str(stmt.compile())
        for table_name, rows in self._tables.items():
            if f"FROM {table_name}" in compiled:
                return _Result(rows)
        return _Result([])


# ---------------------------------------------------------------------------
# Builders de fixtures (shape real de Neon)
# ---------------------------------------------------------------------------

def _zone_state_data(zone_id: str, projected_density: int) -> dict:
    return {
        "zone_id": zone_id,
        "operational_state": "NORMAL",
        "availability": 100,
        "saturation_level": 0.3,
        "estimated_wait": 5,
        "confidence": 0.9,
        "reasoning_factors": [],
        "active_restriction": "OPEN",
        "projected_density": projected_density,
    }


def make_prediction(
    timestamp: datetime,
    zone_states: list[dict],
) -> PredictionModel:
    return PredictionModel(
        id=uuid4(),
        timestamp=timestamp,
        event_day_id=DAY,
        active_phase_id=UUID(PHASE),
        active_event_day_phase_id=UUID(EVENT_DAY_PHASE),
        zone_states_data=zone_states,
    )


def neon_predictions(n: int = 110) -> list[PredictionModel]:
    base = datetime(2026, 8, 1, 0, 5)
    return [
        make_prediction(
            base + timedelta(minutes=5 * i),
            [_zone_state_data(ZONE_A, 400), _zone_state_data(ZONE_B, 300)],
        )
        for i in range(n)
    ]


def make_observation(
    timestamp: datetime,
    zone_id: str,
    observed_density: int,
) -> OperationalObservationModel:
    return OperationalObservationModel(
        id=uuid4(),
        event_day_id=DAY,
        zone_id=zone_id,
        timestamp=timestamp,
        observed_density=observed_density,
        observer_id=None,
        source="manual",
        metadata_=None,
        created_at=timestamp,
    )


def make_event(
    *,
    is_incident: bool,
    start: datetime,
    end: datetime,
) -> OperationalEvent:
    return OperationalEvent(
        id=uuid4(),
        event_day_id=DAY,
        zone_id=ZONE_A,
        event_type="accidente" if is_incident else "corte_calle",
        description=None,
        effect_type="reduccion_capacidad" if is_incident else "incidente_sin_impacto",
        effect_value=30 if is_incident else None,
        is_incident=is_incident,
        start_timestamp=start,
        end_timestamp=end,
        is_active=True,
        created_at=start,
        updated_at=end,
    )


def make_zone(
    zone_id: str,
    type_: str,
    capacity: int,
    subtipo: str | None = None,
) -> Zone:
    return Zone(
        id=zone_id,
        event_id=EVENT,
        name="zona",
        type=type_,
        capacity=capacity,
        subtipo=subtipo,
    )


def make_zone_type(zone_type_id: str, slug: str) -> ZoneType:
    return ZoneType(
        id=zone_type_id,
        name=slug,
        slug=slug,
        icon="",
        description="",
        default_factors={},
    )


def make_behavior(
    zone_type_id: str,
    density_factor: float,
    phase_id: str = PHASE,
) -> ZoneBehaviorModel:
    return ZoneBehaviorModel(
        id=uuid4(),
        operational_phase_id=UUID(phase_id),
        zone_type_id=UUID(zone_type_id),
        density_factor=density_factor,
        flow_restriction=FlowRestriction.OPEN,
    )


def neon_behaviors(n: int = 110) -> list[ZoneBehaviorModel]:
    behaviors: list[ZoneBehaviorModel] = [
        make_behavior(ZT_A, 0.8),
        make_behavior(ZT_B, 0.5),
    ]
    for i in range(n - 2):
        behaviors.append(
            make_behavior(
                f"aaaaaaaa-aaaa-aaaa-aaaa-aaaa{i:012d}"[:36],
                0.7,
                phase_id=UNAFFECTED_PHASE,
            ),
        )
    return behaviors


def neon_zones() -> list[Zone]:
    return [
        make_zone(ZONE_A, "bano", 500),
        make_zone(ZONE_B, "hidratacion", 400),
        make_zone("cccccccc-cccc-cccc-cccc-cccccccccccc", "servicios", 300, subtipo="banos"),
    ]


def neon_zone_types() -> list[ZoneType]:
    return [
        make_zone_type(ZT_A, "bano"),
        make_zone_type(ZT_B, "hidratacion"),
    ]


def neon_tables() -> dict[str, list]:
    return {
        "predictions": neon_predictions(),
        "operational_observations": [
            make_observation(T_09_10, ZONE_A, 300),
            make_observation(T_09_10, ZONE_B, 250),
        ],
        "operational_events": [
            make_event(is_incident=True, start=T_09_00, end=datetime(2026, 8, 1, 10, 0, 0)),
            make_event(is_incident=False, start=datetime(2026, 8, 1, 11, 0, 0), end=datetime(2026, 8, 1, 12, 0, 0)),
        ],
        "zones": neon_zones(),
        "zone_types": neon_zone_types(),
        "zone_behaviors": neon_behaviors(),
    }


# ---------------------------------------------------------------------------
# MetricService
# ---------------------------------------------------------------------------

class TestDensityDeviation:
    async def test_blocked_when_no_predictions(self) -> None:
        service = MetricService(FakeSession({}))
        result = await service.calculate_density_deviation(DAY)
        assert result.status == "BLOCKED"
        assert result.value is None
        assert "predicciones" in result.reason

    async def test_blocked_when_no_observations(self) -> None:
        service = MetricService(FakeSession({"predictions": neon_predictions()}))
        result = await service.calculate_density_deviation(DAY)
        assert result.status == "BLOCKED"
        assert "observaciones" in result.reason

    async def test_blocked_when_no_contemporaneous_match(self) -> None:
        tables = {
            "predictions": neon_predictions(),
            "operational_observations": [
                make_observation(datetime(2026, 8, 2, 9, 0, 0), ZONE_A, 300),
            ],
        }
        result = await MetricService(FakeSession(tables)).calculate_density_deviation(DAY)
        assert result.status == "BLOCKED"
        assert "ventana" in result.reason

    async def test_blocked_when_zone_capacity_unknown(self) -> None:
        tables = {
            "predictions": [make_prediction(T_09_00, [_zone_state_data(ZONE_A, 400)])],
            "operational_observations": [make_observation(T_09_00, ZONE_A, 300)],
        }
        result = await MetricService(FakeSession(tables)).calculate_density_deviation(DAY)
        assert result.status == "BLOCKED"
        assert result.data_points == 0

    async def test_enabled_with_single_contemporaneous_pair(self) -> None:
        tables = {
            "predictions": [
                make_prediction(T_09_00, [_zone_state_data(ZONE_A, 400), _zone_state_data(ZONE_B, 200)]),
            ],
            "operational_observations": [make_observation(T_09_00, ZONE_A, 300)],
            "zones": [make_zone(ZONE_A, "bano", 500), make_zone(ZONE_B, "bano", 400)],
        }
        result = await MetricService(FakeSession(tables)).calculate_density_deviation(DAY)
        assert result.status == "ENABLED"
        assert result.value == pytest.approx(abs(400 - 300) / 500)
        assert result.data_points == 1
        assert result.limitations

    async def test_enabled_with_real_neon_shape(self) -> None:
        result = await MetricService(FakeSession(neon_tables())).calculate_density_deviation(DAY)
        assert result.status == "ENABLED"
        assert result.value > 0
        assert result.data_points > 0

    async def test_limitations_documented(self) -> None:
        result = await MetricService(FakeSession(neon_tables())).calculate_density_deviation(DAY)
        assert len(result.limitations) >= 3


class TestIncidentFrequency:
    async def test_blocked_when_no_events(self) -> None:
        result = await MetricService(FakeSession({})).calculate_incident_frequency(DAY)
        assert result.status == "BLOCKED"
        assert result.value is None

    async def test_limited_when_events_but_zero_incidents(self) -> None:
        tables = {
            "operational_events": [
                make_event(is_incident=False, start=T_09_00, end=datetime(2026, 8, 1, 10, 0, 0)),
            ],
        }
        result = await MetricService(FakeSession(tables)).calculate_incident_frequency(DAY)
        assert result.status == "LIMITED"
        assert result.value == 0.0
        assert result.data_points == 0

    async def test_enabled_with_incidents(self) -> None:
        tables = {
            "operational_events": [
                make_event(is_incident=True, start=T_09_00, end=datetime(2026, 8, 1, 10, 0, 0)),
                make_event(is_incident=False, start=datetime(2026, 8, 1, 11, 0, 0), end=datetime(2026, 8, 1, 12, 0, 0)),
            ],
        }
        result = await MetricService(FakeSession(tables)).calculate_incident_frequency(DAY)
        assert result.status == "ENABLED"
        assert result.value == pytest.approx(1 / 3)
        assert result.data_points == 1

    async def test_blocked_when_hours_range_is_zero(self) -> None:
        tables = {
            "operational_events": [
                make_event(is_incident=True, start=T_09_00, end=T_09_00),
            ],
        }
        result = await MetricService(FakeSession(tables)).calculate_incident_frequency(DAY)
        assert result.status == "BLOCKED"
        assert result.value is None


class TestPhaseTransitionLatency:
    async def test_always_blocked(self) -> None:
        result = MetricService.calculate_phase_transition_latency()
        assert result.status == "BLOCKED"
        assert result.value is None
        assert result.data_points == 0
        assert result.limitations


class TestZoneBehaviorAdherence:
    async def test_blocked_when_no_behaviors(self) -> None:
        result = await MetricService(FakeSession({})).calculate_zone_behavior_adherence(DAY, PHASE)
        assert result.status == "BLOCKED"
        assert "zone_behaviors" in result.reason

    async def test_blocked_when_no_observations(self) -> None:
        tables = {"zone_behaviors": [make_behavior(ZT_A, 0.8)]}
        result = await MetricService(FakeSession(tables)).calculate_zone_behavior_adherence(DAY, PHASE)
        assert result.status == "BLOCKED"
        assert "observaciones" in result.reason

    async def test_blocked_when_observations_have_no_applicable_behavior(self) -> None:
        tables = {
            "zone_behaviors": [make_behavior("99999999-9999-9999-9999-999999999999", 0.8)],
            "operational_observations": [make_observation(T_09_00, ZONE_A, 300)],
            "zones": [make_zone(ZONE_A, "bano", 500)],
            "zone_types": [make_zone_type(ZT_A, "bano")],
        }
        result = await MetricService(FakeSession(tables)).calculate_zone_behavior_adherence(DAY, PHASE)
        assert result.status == "BLOCKED"
        assert result.data_points == 0

    async def test_enabled_with_real_neon_shape(self) -> None:
        result = await MetricService(FakeSession(neon_tables())).calculate_zone_behavior_adherence(DAY, PHASE)
        assert result.status == "ENABLED"
        assert result.data_points == 2
        expected_a = 1.0 - abs(300 - 500 * 0.8) / 500
        expected_b = 1.0 - abs(250 - 400 * 0.5) / 400
        assert result.value == pytest.approx((expected_a + expected_b) / 2)
        assert any("accumulated_impact" in limit for limit in result.limitations)

    async def test_subtipo_fallback_resolves_zone_type(self) -> None:
        tables = {
            "zone_behaviors": [make_behavior(ZT_A, 0.8)],
            "operational_observations": [make_observation(T_09_00, "cccccccc-cccc-cccc-cccc-cccccccccccc", 200)],
            "zones": [make_zone("cccccccc-cccc-cccc-cccc-cccccccccccc", "servicios", 300, subtipo="banos")],
            "zone_types": [make_zone_type(ZT_A, "bano")],
        }
        result = await MetricService(FakeSession(tables)).calculate_zone_behavior_adherence(DAY, PHASE)
        assert result.status == "ENABLED"
        assert result.data_points == 1


class TestCalculateAll:
    async def test_returns_four_metrics_in_defined_order(self) -> None:
        results = await MetricService(FakeSession(neon_tables())).calculate_all(DAY, PHASE)
        assert [r.name for r in results] == [
            "density_deviation",
            "incident_frequency",
            "phase_transition_latency",
            "zone_behavior_adherence",
        ]

    async def test_statuses_are_honest(self) -> None:
        results = await MetricService(FakeSession(neon_tables())).calculate_all(DAY, PHASE)
        assert {r.status for r in results} <= {"ENABLED", "LIMITED", "BLOCKED"}
        for result in results:
            if result.status == "BLOCKED":
                assert result.value is None
            assert result.display_name
            assert isinstance(result.limitations, list)

    async def test_limits_documented_for_enabled_metrics(self) -> None:
        results = await MetricService(FakeSession(neon_tables())).calculate_all(DAY, PHASE)
        enabled = [r for r in results if r.status == "ENABLED"]
        assert enabled
        for result in enabled:
            assert result.limitations


# ---------------------------------------------------------------------------
# SQLPredictionRepository.find_by_event_day_id
# ---------------------------------------------------------------------------

class TestFindByEventDayId:
    def _model(self) -> PredictionModel:
        return PredictionModel(
            id=uuid4(),
            timestamp=T_09_00,
            event_day_id=DAY,
            active_phase_id=UUID(PHASE),
            active_event_day_phase_id=UUID(EVENT_DAY_PHASE),
            zone_states_data=[_zone_state_data(ZONE_A, 400)],
        )

    async def test_filters_by_event_day_id_and_returns_list(self) -> None:
        session = AsyncMock()
        scalars = MagicMock()
        scalars.all.return_value = [self._model()]
        result = MagicMock()
        result.scalars.return_value = scalars
        session.execute = AsyncMock(return_value=result)

        repo = SQLPredictionRepository(session)
        found = await repo.find_by_event_day_id(DAY)

        assert len(found) == 1
        compiled = str(
            session.execute.call_args[0][0].compile(
                compile_kwargs={"literal_binds": True},
            ),
        )
        assert "predictions" in compiled
        assert DAY in compiled

    async def test_returns_empty_list_when_no_rows(self) -> None:
        session = AsyncMock()
        scalars = MagicMock()
        scalars.all.return_value = []
        result = MagicMock()
        result.scalars.return_value = scalars
        session.execute = AsyncMock(return_value=result)

        found = await SQLPredictionRepository(session).find_by_event_day_id(DAY)

        assert found == []

    def test_repository_exposes_method(self) -> None:
        assert hasattr(SQLPredictionRepository, "find_by_event_day_id")