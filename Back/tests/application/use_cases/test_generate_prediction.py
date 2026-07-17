from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.application.context_engine.exceptions import (
    BehaviorNotDefined,
    DomainNotConfigured,
    InvalidConfiguration,
    InvalidPhaseContext,
)
from src.application.use_cases.generate_prediction import GeneratePrediction
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.operational_profile import OperationalProfile
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction, ZoneBehavior
from src.domain.value_objects.territorial_prediction import TerritorialPrediction


@pytest.fixture
def timestamp() -> datetime:
    return datetime(2026, 1, 10, 20, 0)


@pytest.fixture
def peak_phase() -> OperationalPhase:
    return OperationalPhase(
        id=UUID("10000000-0000-0000-0000-000000000001"),
        name="Peak",
        sequence_order=2,
    )


@pytest.fixture
def profile(peak_phase: OperationalPhase) -> OperationalProfile:
    return OperationalProfile(
        id=UUID("20000000-0000-0000-0000-000000000001"),
        name="Test Profile",
        phases=(peak_phase,),
    )


@pytest.fixture
def event_day_phase(peak_phase: OperationalPhase) -> EventDayPhase:
    return EventDayPhase(
        id=UUID("30000000-0000-0000-0000-000000000001"),
        event_day_id=UUID("40000000-0000-0000-0000-000000000001"),
        operational_phase_id=peak_phase.id,
        start_min=1200,
        end_min=1380,
    )


@pytest.fixture
def event_day(
    event_day_phase: EventDayPhase,
    profile: OperationalProfile,
) -> EventDay:
    return EventDay(
        id=UUID("40000000-0000-0000-0000-000000000001"),
        event_date=date(2026, 1, 10),
        operational_profile_id=profile.id,
        attendance_level_id=UUID("50000000-0000-0000-0000-000000000001"),
        operational_start_min=1200,
        operational_end_min=1680,
        phases=(event_day_phase,),
    )


@pytest.fixture
def zones() -> list[Zone]:
    return [
        Zone(
            id=UUID("a0000000-0000-0000-0000-000000000001"),
            name="Test Zone",
            zone_type_id=UUID("b0000000-0000-0000-0000-000000000001"),
            capacity=100,
        ),
    ]


@pytest.fixture
def zone_behaviors(
    peak_phase: OperationalPhase,
) -> dict[tuple[UUID, UUID], ZoneBehavior]:
    key = (UUID("b0000000-0000-0000-0000-000000000001"), peak_phase.id)
    return {
        key: ZoneBehavior(
            id=UUID("c0000000-0000-0000-0000-000000000001"),
            zone_type_id=UUID("b0000000-0000-0000-0000-000000000001"),
            operational_phase_id=peak_phase.id,
            density_factor=0.5,
            flow_restriction=FlowRestriction.OPEN,
        ),
    }


@pytest.fixture
def attendance_level() -> AttendanceLevel:
    return AttendanceLevel(id=UUID("50000000-0000-0000-0000-000000000001"), name="Normal", multiplier=1.0)


@pytest.fixture
def prediction(
    timestamp: datetime,
    peak_phase: OperationalPhase,
    event_day_phase: EventDayPhase,
) -> TerritorialPrediction:
    return TerritorialPrediction(
        timestamp=timestamp,
        zone_states=[],
        active_phase_id=peak_phase.id,
        active_event_day_phase_id=event_day_phase.id,
    )


@pytest.fixture
def engine(prediction: TerritorialPrediction) -> MagicMock:
    eng = MagicMock()
    eng.predict = MagicMock(return_value=prediction)
    return eng


@pytest.fixture
def event_day_repo(event_day: EventDay) -> AsyncMock:
    repo = AsyncMock()
    repo.find_by_date = AsyncMock(return_value=event_day)
    return repo


@pytest.fixture
def operational_event_repo() -> AsyncMock:
    repo = AsyncMock()
    repo.find_active_by_timestamp = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def operational_profile_repo(profile: OperationalProfile) -> AsyncMock:
    repo = AsyncMock()
    repo.find_by_id = AsyncMock(return_value=profile)
    return repo


@pytest.fixture
def prediction_repo(prediction: TerritorialPrediction) -> AsyncMock:
    repo = AsyncMock()
    repo.save = AsyncMock(return_value=prediction)
    return repo


@pytest.fixture
def use_case(
    engine: MagicMock,
    event_day_repo: AsyncMock,
    operational_event_repo: AsyncMock,
    operational_profile_repo: AsyncMock,
    prediction_repo: AsyncMock,
) -> GeneratePrediction:
    return GeneratePrediction(
        engine=engine,
        event_day_repo=event_day_repo,
        operational_event_repo=operational_event_repo,
        operational_profile_repo=operational_profile_repo,
        prediction_repo=prediction_repo,
    )


class TestGeneratePrediction:
    async def test_invokes_engine_once(
        self,
        use_case: GeneratePrediction,
        engine: MagicMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        result = await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
        )

        assert engine.predict.call_count == 1
        assert isinstance(result, TerritorialPrediction)

    async def test_passes_correct_parameters_to_engine(
        self,
        use_case: GeneratePrediction,
        engine: MagicMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
        event_day: EventDay,
        profile: OperationalProfile,
    ) -> None:
        await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
        )

        expected_phases = {p.id: p for p in profile.phases}
        engine.predict.assert_called_once_with(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            operational_phases=expected_phases,
            attendance_level=attendance_level,
            event_day=event_day,
            events=[],
        )

    async def test_returns_prediction_from_engine(
        self,
        use_case: GeneratePrediction,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
        prediction: TerritorialPrediction,
    ) -> None:
        result = await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
        )

        assert result is prediction

    async def test_calls_repositories_in_order(
        self,
        use_case: GeneratePrediction,
        event_day_repo: AsyncMock,
        operational_profile_repo: AsyncMock,
        operational_event_repo: AsyncMock,
        engine: MagicMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
        )

        event_day_repo.find_by_date.assert_awaited_once_with(timestamp.date())
        operational_profile_repo.find_by_id.assert_awaited_once()
        operational_event_repo.find_active_by_timestamp.assert_awaited_once_with(timestamp)

    async def test_raises_domain_not_configured_when_no_event_day(
        self,
        use_case: GeneratePrediction,
        event_day_repo: AsyncMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        event_day_repo.find_by_date = AsyncMock(return_value=None)

        with pytest.raises(DomainNotConfigured):
            await use_case.execute(
                timestamp=timestamp,
                zones=zones,
                zone_behaviors=zone_behaviors,
                attendance_level=attendance_level,
            )

    async def test_raises_invalid_configuration_when_no_profile(
        self,
        use_case: GeneratePrediction,
        operational_profile_repo: AsyncMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        operational_profile_repo.find_by_id = AsyncMock(return_value=None)

        with pytest.raises(InvalidConfiguration):
            await use_case.execute(
                timestamp=timestamp,
                zones=zones,
                zone_behaviors=zone_behaviors,
                attendance_level=attendance_level,
            )

    async def test_propagates_engine_errors(
        self,
        use_case: GeneratePrediction,
        engine: MagicMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        engine.predict = MagicMock(side_effect=InvalidPhaseContext("test"))

        with pytest.raises(InvalidPhaseContext):
            await use_case.execute(
                timestamp=timestamp,
                zones=zones,
                zone_behaviors=zone_behaviors,
                attendance_level=attendance_level,
            )

    async def test_propagates_behavior_not_defined(
        self,
        use_case: GeneratePrediction,
        engine: MagicMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        engine.predict = MagicMock(
            side_effect=BehaviorNotDefined(
                UUID("00000000-0000-0000-0000-000000000001"),
                UUID("00000000-0000-0000-0000-000000000002"),
            )
        )

        with pytest.raises(BehaviorNotDefined):
            await use_case.execute(
                timestamp=timestamp,
                zones=zones,
                zone_behaviors=zone_behaviors,
                attendance_level=attendance_level,
            )

    async def test_does_not_call_engine_when_event_day_missing(
        self,
        use_case: GeneratePrediction,
        engine: MagicMock,
        event_day_repo: AsyncMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        event_day_repo.find_by_date = AsyncMock(return_value=None)

        with pytest.raises(DomainNotConfigured):
            await use_case.execute(
                timestamp=timestamp,
                zones=zones,
                zone_behaviors=zone_behaviors,
                attendance_level=attendance_level,
            )

        engine.predict.assert_not_called()

    async def test_does_not_call_engine_when_profile_missing(
        self,
        use_case: GeneratePrediction,
        engine: MagicMock,
        operational_profile_repo: AsyncMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        operational_profile_repo.find_by_id = AsyncMock(return_value=None)

        with pytest.raises(InvalidConfiguration):
            await use_case.execute(
                timestamp=timestamp,
                zones=zones,
                zone_behaviors=zone_behaviors,
                attendance_level=attendance_level,
            )

        engine.predict.assert_not_called()

    async def test_saves_prediction_once(
        self,
        use_case: GeneratePrediction,
        prediction_repo: AsyncMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
        )

        prediction_repo.save.assert_awaited_once()

    async def test_save_receives_prediction_from_engine(
        self,
        use_case: GeneratePrediction,
        prediction_repo: AsyncMock,
        engine: MagicMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
        prediction: TerritorialPrediction,
    ) -> None:
        await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
        )

        prediction_repo.save.assert_awaited_once_with(prediction)

    async def test_does_not_save_when_engine_fails(
        self,
        use_case: GeneratePrediction,
        prediction_repo: AsyncMock,
        engine: MagicMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        engine.predict = MagicMock(side_effect=InvalidPhaseContext("test"))

        with pytest.raises(InvalidPhaseContext):
            await use_case.execute(
                timestamp=timestamp,
                zones=zones,
                zone_behaviors=zone_behaviors,
                attendance_level=attendance_level,
            )

        prediction_repo.save.assert_not_called()

    async def test_propagates_save_error(
        self,
        use_case: GeneratePrediction,
        prediction_repo: AsyncMock,
        engine: MagicMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        prediction_repo.save = AsyncMock(side_effect=RuntimeError("DB failure"))

        with pytest.raises(RuntimeError):
            await use_case.execute(
                timestamp=timestamp,
                zones=zones,
                zone_behaviors=zone_behaviors,
                attendance_level=attendance_level,
            )

    async def test_returns_saved_prediction(
        self,
        use_case: GeneratePrediction,
        prediction_repo: AsyncMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
        prediction: TerritorialPrediction,
    ) -> None:
        result = await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
        )

        assert result is prediction
