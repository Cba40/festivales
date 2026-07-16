from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from src.domain.entities.operational_event import OperationalEvent
from src.infrastructure.persistence.models import OperationalEventModel
from src.infrastructure.persistence.repositories import (
    SQLOperationalEventRepository,
)

A_UUID = UUID("11111111-1111-1111-1111-111111111111")
B_UUID = UUID("22222222-2222-2222-2222-222222222222")
C_UUID = UUID("33333333-3333-3333-3333-333333333333")


def _mock_scalars_result(models: list) -> MagicMock:
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=models)
    result = MagicMock()
    result.scalars = MagicMock(return_value=scalars_mock)
    return result


class TestSQLOperationalEventRepository:
    async def test_find_active_by_timestamp_returns_events(self) -> None:
        session = AsyncMock()
        model1 = OperationalEventModel(
            id=A_UUID,
            target_zone_id=B_UUID,
            impact_value=-50,
            is_incident=False,
            start_timestamp=datetime(2026, 7, 10, 8, 0, 0),
            end_timestamp=datetime(2026, 7, 10, 12, 0, 0),
        )
        model2 = OperationalEventModel(
            id=B_UUID,
            target_zone_id=C_UUID,
            impact_value=-100,
            is_incident=True,
            start_timestamp=datetime(2026, 7, 10, 9, 0, 0),
            end_timestamp=datetime(2026, 7, 10, 11, 0, 0),
        )
        session.execute = AsyncMock(
            return_value=_mock_scalars_result([model1, model2])
        )
        repo = SQLOperationalEventRepository(session)

        result = await repo.find_active_by_timestamp(
            datetime(2026, 7, 10, 10, 0, 0)
        )

        assert len(result) == 2
        assert isinstance(result[0], OperationalEvent)
        assert result[0].id == A_UUID
        assert result[0].impact_value == -50
        assert result[1].id == B_UUID
        assert result[1].is_incident is True

    async def test_find_active_by_timestamp_returns_empty_when_no_events(
        self,
    ) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalars_result([]))
        repo = SQLOperationalEventRepository(session)

        result = await repo.find_active_by_timestamp(
            datetime(2026, 7, 10, 10, 0, 0)
        )

        assert len(result) == 0

    async def test_find_active_by_timestamp_applies_temporal_filter(
        self,
    ) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalars_result([]))
        repo = SQLOperationalEventRepository(session)

        ts = datetime(2026, 7, 10, 10, 0, 0)
        await repo.find_active_by_timestamp(ts)

        call_args = session.execute.call_args[0][0]
        compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
        assert "operational_events" in compiled
        assert "start_timestamp" in compiled
        assert "end_timestamp" in compiled

    async def test_find_active_by_timestamp_uses_async_session_injected(
        self,
    ) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalars_result([]))
        repo = SQLOperationalEventRepository(session)

        await repo.find_active_by_timestamp(
            datetime(2026, 7, 10, 10, 0, 0)
        )

        session.execute.assert_awaited_once()

    def test_implements_operational_event_repository_port(self) -> None:
        from src.domain.ports.operational_event_repository import (
            OperationalEventRepository,
        )

        assert OperationalEventRepository.__name__ in [
            b.__name__ for b in SQLOperationalEventRepository.__mro__
        ], "SQLOperationalEventRepository does not inherit from OperationalEventRepository"
        assert hasattr(SQLOperationalEventRepository, "find_active_by_timestamp")
