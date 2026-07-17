from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.application.use_cases.get_prediction import GetTerritorialPrediction
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import ZoneBehavior
from src.domain.value_objects.territorial_prediction import TerritorialPrediction


@pytest.fixture
def timestamp() -> datetime:
    return datetime(2026, 1, 10, 20, 0)


@pytest.fixture
def zones() -> list[Zone]:
    return []


@pytest.fixture
def zone_behaviors() -> dict[tuple[UUID, UUID], ZoneBehavior]:
    return {}


@pytest.fixture
def attendance_level() -> AttendanceLevel:
    return AttendanceLevel(
        id=UUID("50000000-0000-0000-0000-000000000001"),
        name="Normal",
        multiplier=1.0,
    )


@pytest.fixture
def prediction(timestamp: datetime) -> TerritorialPrediction:
    return TerritorialPrediction(
        timestamp=timestamp,
        zone_states=[],
        active_phase_id=UUID("10000000-0000-0000-0000-000000000001"),
        active_event_day_phase_id=UUID("30000000-0000-0000-0000-000000000001"),
    )


@pytest.fixture
def prediction_repo(
    prediction: TerritorialPrediction,
) -> AsyncMock:
    repo = AsyncMock()
    repo.find_by_timestamp = AsyncMock(return_value=None)
    repo.save = AsyncMock()
    return repo


@pytest.fixture
def generate_prediction(
    prediction: TerritorialPrediction,
) -> AsyncMock:
    gp = AsyncMock()
    gp.execute = AsyncMock(return_value=prediction)
    return gp


@pytest.fixture
def use_case(
    prediction_repo: AsyncMock,
    generate_prediction: AsyncMock,
) -> GetTerritorialPrediction:
    return GetTerritorialPrediction(
        prediction_repo=prediction_repo,
        generate_prediction=generate_prediction,
    )


class TestGetTerritorialPrediction:
    async def test_returns_existing_prediction_when_available(
        self,
        use_case: GetTerritorialPrediction,
        prediction_repo: AsyncMock,
        prediction: TerritorialPrediction,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        prediction_repo.find_by_timestamp = AsyncMock(return_value=prediction)

        result = await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
        )

        assert result is prediction

    async def test_does_not_generate_when_cached(
        self,
        use_case: GetTerritorialPrediction,
        prediction_repo: AsyncMock,
        generate_prediction: AsyncMock,
        prediction: TerritorialPrediction,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        prediction_repo.find_by_timestamp = AsyncMock(return_value=prediction)

        await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
        )

        generate_prediction.execute.assert_not_awaited()

    async def test_generates_when_not_cached(
        self,
        use_case: GetTerritorialPrediction,
        generate_prediction: AsyncMock,
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

        generate_prediction.execute.assert_awaited_once()

    async def test_returns_generated_prediction(
        self,
        use_case: GetTerritorialPrediction,
        generate_prediction: AsyncMock,
        prediction: TerritorialPrediction,
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

        assert result is prediction

    async def test_does_not_save_again_when_cached(
        self,
        use_case: GetTerritorialPrediction,
        prediction_repo: AsyncMock,
        generate_prediction: AsyncMock,
        prediction: TerritorialPrediction,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        prediction_repo.find_by_timestamp = AsyncMock(return_value=prediction)

        await use_case.execute(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
        )

        generate_prediction.execute.assert_not_awaited()

    async def test_passes_parameters_to_generate_prediction(
        self,
        use_case: GetTerritorialPrediction,
        generate_prediction: AsyncMock,
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

        generate_prediction.execute.assert_awaited_once_with(
            timestamp=timestamp,
            zones=zones,
            zone_behaviors=zone_behaviors,
            attendance_level=attendance_level,
        )

    async def test_propagates_repository_find_error(
        self,
        use_case: GetTerritorialPrediction,
        prediction_repo: AsyncMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        prediction_repo.find_by_timestamp = AsyncMock(
            side_effect=RuntimeError("DB failure"),
        )

        with pytest.raises(RuntimeError, match="DB failure"):
            await use_case.execute(
                timestamp=timestamp,
                zones=zones,
                zone_behaviors=zone_behaviors,
                attendance_level=attendance_level,
            )

    async def test_propagates_generate_prediction_error(
        self,
        use_case: GetTerritorialPrediction,
        generate_prediction: AsyncMock,
        timestamp: datetime,
        zones: list[Zone],
        zone_behaviors: dict[tuple[UUID, UUID], ZoneBehavior],
        attendance_level: AttendanceLevel,
    ) -> None:
        generate_prediction.execute = AsyncMock(
            side_effect=RuntimeError("Generation failed"),
        )

        with pytest.raises(RuntimeError, match="Generation failed"):
            await use_case.execute(
                timestamp=timestamp,
                zones=zones,
                zone_behaviors=zone_behaviors,
                attendance_level=attendance_level,
            )

    async def test_does_not_access_infrastructure(
        self,
        use_case: GetTerritorialPrediction,
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

        assert isinstance(result, TerritorialPrediction)

    async def test_does_not_execute_context_engine_directly(
        self,
        use_case: GetTerritorialPrediction,
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

        assert isinstance(result, TerritorialPrediction)
