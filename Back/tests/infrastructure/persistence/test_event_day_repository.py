from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.infrastructure.persistence.models import (
    EventDayModel,
    EventDayPhaseModel,
)
from src.infrastructure.persistence.repositories import SQLEventDayRepository

A_UUID = UUID("11111111-1111-1111-1111-111111111111")
B_UUID = UUID("22222222-2222-2222-2222-222222222222")
C_UUID = UUID("33333333-3333-3333-3333-333333333333")


def _mock_scalar_result(model_or_none):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=model_or_none)
    return result


class TestSQLEventDayRepository:
    async def test_find_by_date_returns_event_day(self) -> None:
        session = AsyncMock()
        phase_model = EventDayPhaseModel(
            id=A_UUID,
            event_day_id=B_UUID,
            operational_phase_id=C_UUID,
            start_min=480,
            end_min=720,
        )
        model = EventDayModel(
            id=B_UUID,
            event_date=date(2026, 7, 10),
            operational_profile_id=C_UUID,
            attendance_level_id=uuid4(),
            operational_start_min=480,
            operational_end_min=1380,
        )
        model.phases = [phase_model]

        session.execute = AsyncMock(return_value=_mock_scalar_result(model))
        repo = SQLEventDayRepository(session)

        result = await repo.find_by_date(date(2026, 7, 10))

        assert result is not None
        assert isinstance(result, EventDay)
        assert result.id == B_UUID
        assert result.event_date == date(2026, 7, 10)
        assert len(result.phases) == 1
        assert result.phases[0].id == A_UUID

    async def test_find_by_date_returns_none_when_not_found(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar_result(None))
        repo = SQLEventDayRepository(session)

        result = await repo.find_by_date(date(2026, 7, 11))

        assert result is None

    async def test_find_by_date_applies_filter(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar_result(None))
        repo = SQLEventDayRepository(session)

        await repo.find_by_date(date(2026, 7, 15))

        call_args = session.execute.call_args[0][0]
        compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
        assert "event_days" in compiled
        assert "2026-07-15" in compiled

    async def test_find_by_date_loads_phases_aggregate(self) -> None:
        session = AsyncMock()
        phase_model = EventDayPhaseModel(
            id=A_UUID,
            event_day_id=B_UUID,
            operational_phase_id=C_UUID,
            start_min=480,
            end_min=720,
        )
        model = EventDayModel(
            id=B_UUID,
            event_date=date(2026, 7, 10),
            operational_profile_id=C_UUID,
            attendance_level_id=uuid4(),
            operational_start_min=480,
            operational_end_min=1380,
        )
        model.phases = [phase_model]

        session.execute = AsyncMock(return_value=_mock_scalar_result(model))
        repo = SQLEventDayRepository(session)

        result = await repo.find_by_date(date(2026, 7, 10))

        assert result is not None
        assert len(result.phases) == 1
        assert result.phases[0].event_day_id == B_UUID
        assert result.phases[0].start_min == 480
        assert result.phases[0].end_min == 720

    async def test_find_by_date_returns_domain_entity_via_mapper(self) -> None:
        session = AsyncMock()
        phase_model = EventDayPhaseModel(
            id=A_UUID,
            event_day_id=B_UUID,
            operational_phase_id=C_UUID,
            start_min=480,
            end_min=1380,
        )
        model = EventDayModel(
            id=B_UUID,
            event_date=date(2026, 7, 10),
            operational_profile_id=C_UUID,
            attendance_level_id=uuid4(),
            operational_start_min=480,
            operational_end_min=1380,
        )
        model.phases = [phase_model]
        session.execute = AsyncMock(return_value=_mock_scalar_result(model))
        repo = SQLEventDayRepository(session)

        result = await repo.find_by_date(date(2026, 7, 10))

        assert isinstance(result, EventDay)
        assert result.id == B_UUID
        assert isinstance(result.phases[0], EventDayPhase)

    async def test_find_by_date_uses_async_session_injected(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar_result(None))
        repo = SQLEventDayRepository(session)

        await repo.find_by_date(date(2026, 7, 15))

        session.execute.assert_awaited_once()

    def test_implements_event_day_repository_port(self) -> None:
        from src.domain.ports.event_day_repository import EventDayRepository

        assert EventDayRepository.__name__ in [
            b.__name__ for b in SQLEventDayRepository.__mro__
        ], "SQLEventDayRepository does not inherit from EventDayRepository"
        assert hasattr(SQLEventDayRepository, "find_by_date")
        assert hasattr(SQLEventDayRepository, "save")


# ---------------------------------------------------------------------------
# save()
# ---------------------------------------------------------------------------


class TestSQLEventDayRepositorySave:
    ATTENDANCE_ID = uuid4()

    def _make_phase(self, id: UUID, start_min: int, end_min: int) -> EventDayPhase:
        return EventDayPhase(
            id=id,
            event_day_id=B_UUID,
            operational_phase_id=C_UUID,
            start_min=start_min,
            end_min=end_min,
        )

    def _make_event_day(
        self, id: UUID, phases: tuple[EventDayPhase, ...]
    ) -> EventDay:
        return EventDay(
            id=id,
            event_date=date(2026, 7, 10),
            operational_profile_id=C_UUID,
            attendance_level_id=self.ATTENDANCE_ID,
            operational_start_min=480,
            operational_end_min=1380,
            phases=phases,
        )

    async def test_save_new_aggregate(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        phase = self._make_phase(A_UUID, 480, 720)
        event_day = self._make_event_day(B_UUID, (phase,))

        repo = SQLEventDayRepository(session)
        result = await repo.save(event_day)

        assert result.id == B_UUID
        assert result.event_date == date(2026, 7, 10)
        assert len(result.phases) == 1
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    async def test_save_updates_existing_aggregate(self) -> None:
        session = AsyncMock()
        existing_phase = EventDayPhaseModel(
            id=A_UUID,
            event_day_id=B_UUID,
            operational_phase_id=C_UUID,
            start_min=480,
            end_min=720,
        )
        existing_model = EventDayModel(
            id=B_UUID,
            event_date=date(2026, 7, 10),
            operational_profile_id=C_UUID,
            attendance_level_id=self.ATTENDANCE_ID,
            operational_start_min=480,
            operational_end_min=1380,
        )
        existing_model.phases = [existing_phase]

        session.get = AsyncMock(return_value=existing_model)
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        phase = self._make_phase(A_UUID, 600, 900)
        event_day = self._make_event_day(B_UUID, (phase,))

        repo = SQLEventDayRepository(session)
        result = await repo.save(event_day)

        assert existing_model.operational_start_min == 480
        assert existing_model.operational_end_min == 1380
        assert existing_model.phases[0].start_min == 600
        assert existing_model.phases[0].end_min == 900
        session.flush.assert_awaited_once()

    async def test_save_adds_new_phases(self) -> None:
        session = AsyncMock()
        existing_phase = EventDayPhaseModel(
            id=A_UUID,
            event_day_id=B_UUID,
            operational_phase_id=C_UUID,
            start_min=480,
            end_min=720,
        )
        existing_model = EventDayModel(
            id=B_UUID,
            event_date=date(2026, 7, 10),
            operational_profile_id=C_UUID,
            attendance_level_id=self.ATTENDANCE_ID,
            operational_start_min=480,
            operational_end_min=1380,
        )
        existing_model.phases = [existing_phase]

        session.get = AsyncMock(return_value=existing_model)
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        new_id = UUID("44444444-4444-4444-4444-444444444444")
        phase1 = self._make_phase(A_UUID, 480, 720)
        phase2 = self._make_phase(new_id, 720, 1380)
        event_day = self._make_event_day(B_UUID, (phase1, phase2))

        repo = SQLEventDayRepository(session)
        result = await repo.save(event_day)

        assert len(result.phases) == 2
        assert len(existing_model.phases) == 2
        assert existing_model.phases[1].id == new_id
        assert existing_model.phases[1].start_min == 720

    async def test_save_removes_orphaned_phases(self) -> None:
        session = AsyncMock()
        orphan_phase = EventDayPhaseModel(
            id=C_UUID,
            event_day_id=B_UUID,
            operational_phase_id=A_UUID,
            start_min=480,
            end_min=720,
        )
        existing_model = EventDayModel(
            id=B_UUID,
            event_date=date(2026, 7, 10),
            operational_profile_id=C_UUID,
            attendance_level_id=self.ATTENDANCE_ID,
            operational_start_min=480,
            operational_end_min=1380,
        )
        existing_model.phases = [orphan_phase]

        async def get_side_effect(model_class, ident, **kw):
            if ident == B_UUID:
                return existing_model
            if ident == C_UUID:
                return orphan_phase
            return None

        session.get = AsyncMock(side_effect=get_side_effect)
        session.delete = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        new_phase = self._make_phase(A_UUID, 480, 1380)
        event_day = self._make_event_day(B_UUID, (new_phase,))

        repo = SQLEventDayRepository(session)
        result = await repo.save(event_day)

        assert len(result.phases) == 1
        assert result.phases[0].id == A_UUID
        session.delete.assert_called_once_with(orphan_phase)

    async def test_save_updates_existing_phases(self) -> None:
        session = AsyncMock()
        existing_phase = EventDayPhaseModel(
            id=A_UUID,
            event_day_id=B_UUID,
            operational_phase_id=C_UUID,
            start_min=480,
            end_min=720,
        )
        existing_model = EventDayModel(
            id=B_UUID,
            event_date=date(2026, 7, 10),
            operational_profile_id=C_UUID,
            attendance_level_id=self.ATTENDANCE_ID,
            operational_start_min=480,
            operational_end_min=1380,
        )
        existing_model.phases = [existing_phase]

        session.get = AsyncMock(return_value=existing_model)
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        updated_phase = self._make_phase(A_UUID, 600, 900)
        event_day = self._make_event_day(B_UUID, (updated_phase,))

        repo = SQLEventDayRepository(session)
        result = await repo.save(event_day)

        assert existing_phase.start_min == 600
        assert existing_phase.end_min == 900
        assert existing_phase.operational_phase_id == C_UUID

    async def test_save_uses_flush(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        phase = self._make_phase(A_UUID, 480, 720)
        event_day = self._make_event_day(B_UUID, (phase,))

        repo = SQLEventDayRepository(session)
        await repo.save(event_day)

        session.flush.assert_awaited_once()

    async def test_save_never_calls_commit(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        phase = self._make_phase(A_UUID, 480, 720)
        event_day = self._make_event_day(B_UUID, (phase,))

        repo = SQLEventDayRepository(session)
        await repo.save(event_day)

        session.commit.assert_not_called()

    async def test_save_never_calls_rollback(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        phase = self._make_phase(A_UUID, 480, 720)
        event_day = self._make_event_day(B_UUID, (phase,))

        repo = SQLEventDayRepository(session)
        await repo.save(event_day)

        session.rollback.assert_not_called()

    async def test_save_returns_domain_entity(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        phase = self._make_phase(A_UUID, 480, 720)
        event_day = self._make_event_day(B_UUID, (phase,))

        repo = SQLEventDayRepository(session)
        result = await repo.save(event_day)

        assert isinstance(result, EventDay)
        assert result.id == B_UUID
        assert len(result.phases) == 1
        assert isinstance(result.phases[0], EventDayPhase)
