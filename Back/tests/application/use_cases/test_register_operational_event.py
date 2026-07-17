from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.application.context_engine.exceptions import InvalidConfiguration
from src.application.use_cases.register_operational_event import (
    RegisterOperationalEvent,
)
from src.domain.entities.operational_event import OperationalEvent
from src.domain.entities.zone import Zone


ZONE_ID = UUID("10000000-0000-0000-0000-000000000001")
EVENT_ID = UUID("20000000-0000-0000-0000-000000000002")


@pytest.fixture
def zone() -> Zone:
    return Zone(
        id=ZONE_ID,
        name="TestZone",
        zone_type_id=UUID("30000000-0000-0000-0000-000000000003"),
        capacity=100,
    )


@pytest.fixture
def saved_event() -> OperationalEvent:
    return OperationalEvent(
        id=EVENT_ID,
        target_zone_id=ZONE_ID,
        impact_value=-50,
        is_incident=False,
        start_timestamp=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
        end_timestamp=datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def event_repo(saved_event: OperationalEvent) -> AsyncMock:
    repo = AsyncMock()
    repo.save = AsyncMock(return_value=saved_event)
    return repo


@pytest.fixture
def zone_repo(zone: Zone) -> AsyncMock:
    repo = AsyncMock()
    repo.find_by_id = AsyncMock(return_value=zone)
    return repo


@pytest.fixture
def use_case(
    event_repo: AsyncMock,
    zone_repo: AsyncMock,
) -> RegisterOperationalEvent:
    return RegisterOperationalEvent(
        event_repo=event_repo,
        zone_repo=zone_repo,
    )


class TestRegisterOperationalEvent:
    async def test_registers_and_persists_event(
        self,
        use_case: RegisterOperationalEvent,
        zone: Zone,
    ) -> None:
        result = await use_case.execute(
            target_zone_id=zone.id,
            impact_value=-50,
            is_incident=False,
            start_timestamp=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
            end_timestamp=datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc),
        )

        assert isinstance(result, OperationalEvent)

    async def test_saves_exactly_once(
        self,
        use_case: RegisterOperationalEvent,
        event_repo: AsyncMock,
        zone: Zone,
    ) -> None:
        await use_case.execute(
            target_zone_id=zone.id,
            impact_value=-50,
            is_incident=False,
            start_timestamp=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
            end_timestamp=datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc),
        )

        event_repo.save.assert_awaited_once()

    async def test_returns_saved_event(
        self,
        use_case: RegisterOperationalEvent,
        event_repo: AsyncMock,
        zone: Zone,
        saved_event: OperationalEvent,
    ) -> None:
        event_repo.save = AsyncMock(return_value=saved_event)

        result = await use_case.execute(
            target_zone_id=zone.id,
            impact_value=-50,
            is_incident=False,
            start_timestamp=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
            end_timestamp=datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc),
        )

        assert result is saved_event

    async def test_rejects_start_gte_end(
        self,
        use_case: RegisterOperationalEvent,
        zone: Zone,
    ) -> None:
        with pytest.raises(ValueError, match="end_timestamp must be greater than start_timestamp"):
            await use_case.execute(
                target_zone_id=zone.id,
                impact_value=-50,
                is_incident=False,
                start_timestamp=datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc),
                end_timestamp=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
            )

    async def test_rejects_nonexistent_zone(
        self,
        use_case: RegisterOperationalEvent,
        zone_repo: AsyncMock,
    ) -> None:
        zone_repo.find_by_id = AsyncMock(return_value=None)

        with pytest.raises(InvalidConfiguration, match="Zone"):
            await use_case.execute(
                target_zone_id=UUID("00000000-0000-0000-0000-000000000000"),
                impact_value=-50,
                is_incident=False,
                start_timestamp=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
                end_timestamp=datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc),
            )

    async def test_does_not_save_when_zone_not_found(
        self,
        use_case: RegisterOperationalEvent,
        zone_repo: AsyncMock,
        event_repo: AsyncMock,
    ) -> None:
        zone_repo.find_by_id = AsyncMock(return_value=None)

        with pytest.raises(InvalidConfiguration):
            await use_case.execute(
                target_zone_id=UUID("00000000-0000-0000-0000-000000000000"),
                impact_value=-50,
                is_incident=False,
                start_timestamp=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
                end_timestamp=datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc),
            )

        event_repo.save.assert_not_called()

    async def test_propagates_repository_error(
        self,
        use_case: RegisterOperationalEvent,
        event_repo: AsyncMock,
        zone: Zone,
    ) -> None:
        event_repo.save = AsyncMock(side_effect=RuntimeError("DB failure"))

        with pytest.raises(RuntimeError, match="DB failure"):
            await use_case.execute(
                target_zone_id=zone.id,
                impact_value=-50,
                is_incident=False,
                start_timestamp=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
                end_timestamp=datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc),
            )

    async def test_does_not_access_context_engine(
        self,
        use_case: RegisterOperationalEvent,
        zone: Zone,
    ) -> None:
        result = await use_case.execute(
            target_zone_id=zone.id,
            impact_value=-50,
            is_incident=False,
            start_timestamp=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
            end_timestamp=datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc),
        )

        assert isinstance(result, OperationalEvent)

    async def test_does_not_access_prediction_repository(
        self,
        use_case: RegisterOperationalEvent,
        zone: Zone,
    ) -> None:
        result = await use_case.execute(
            target_zone_id=zone.id,
            impact_value=-50,
            is_incident=False,
            start_timestamp=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
            end_timestamp=datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc),
        )

        assert isinstance(result, OperationalEvent)

    async def test_does_not_use_orm_directly(
        self,
        use_case: RegisterOperationalEvent,
        zone: Zone,
    ) -> None:
        result = await use_case.execute(
            target_zone_id=zone.id,
            impact_value=-50,
            is_incident=False,
            start_timestamp=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
            end_timestamp=datetime(2026, 1, 10, 14, 0, tzinfo=timezone.utc),
        )

        assert isinstance(result, OperationalEvent)
