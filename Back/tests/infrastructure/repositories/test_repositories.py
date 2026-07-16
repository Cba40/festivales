from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.operational_profile import OperationalProfile
from src.domain.entities.zone_behavior import FlowRestriction, ZoneBehavior
from src.infrastructure.persistence.models import (
    EventDayModel,
    EventDayPhaseModel,
    OperationalPhaseModel,
    OperationalProfileModel,
    ZoneBehaviorModel,
)
from src.infrastructure.persistence.repositories import (
    SQLEventDayRepository,
    SQLOperationalProfileRepository,
    SQLZoneBehaviorRepository,
)

A_UUID = UUID("11111111-1111-1111-1111-111111111111")
B_UUID = UUID("22222222-2222-2222-2222-222222222222")
C_UUID = UUID("33333333-3333-3333-3333-333333333333")


def _mock_scalar_result(model_or_none):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=model_or_none)
    return result


def _mock_scalars_result(models):
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.__iter__.return_value = iter(models)
    result.scalars = MagicMock(return_value=scalars_mock)
    return result


# ---------------------------------------------------------------------------
# SQLEventDayRepository
# ---------------------------------------------------------------------------


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

    async def test_find_by_date_uses_correct_filter(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar_result(None))
        repo = SQLEventDayRepository(session)

        await repo.find_by_date(date(2026, 7, 15))

        call_args = session.execute.call_args[0][0]
        compiled = call_args.compile(compile_kwargs={"literal_binds": True})
        assert "event_days" in str(compiled)
        assert "2026-07-15" in str(compiled)

    async def test_find_by_date_uses_mapper(self) -> None:
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


# ---------------------------------------------------------------------------
# SQLZoneBehaviorRepository
# ---------------------------------------------------------------------------


class TestSQLZoneBehaviorRepository:
    async def test_find_by_zone_type_and_phase_returns_behavior(self) -> None:
        session = AsyncMock()
        model = ZoneBehaviorModel(
            id=A_UUID,
            zone_type_id=B_UUID,
            operational_phase_id=C_UUID,
            density_factor=0.75,
            flow_restriction=FlowRestriction.REGULATED,
        )
        session.execute = AsyncMock(return_value=_mock_scalar_result(model))
        repo = SQLZoneBehaviorRepository(session)

        result = await repo.find_by_zone_type_and_phase(B_UUID, C_UUID)

        assert result is not None
        assert isinstance(result, ZoneBehavior)
        assert result.id == A_UUID
        assert result.zone_type_id == B_UUID
        assert result.operational_phase_id == C_UUID
        assert result.density_factor == 0.75
        assert result.flow_restriction == FlowRestriction.REGULATED

    async def test_find_by_zone_type_and_phase_returns_none(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar_result(None))
        repo = SQLZoneBehaviorRepository(session)

        result = await repo.find_by_zone_type_and_phase(B_UUID, C_UUID)

        assert result is None

    async def test_find_by_zone_type_and_phase_uses_both_filters(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar_result(None))
        repo = SQLZoneBehaviorRepository(session)

        await repo.find_by_zone_type_and_phase(B_UUID, C_UUID)

        call_args = session.execute.call_args[0][0]
        compiled = str(call_args.compile(compile_kwargs={"literal_binds": True}))
        assert "zone_type_id" in compiled
        assert "operational_phase_id" in compiled
        assert B_UUID.hex in compiled
        assert C_UUID.hex in compiled


# ---------------------------------------------------------------------------
# SQLOperationalProfileRepository
# ---------------------------------------------------------------------------


class TestSQLOperationalProfileRepository:
    async def test_find_by_id_returns_profile(self) -> None:
        session = AsyncMock()
        phase_model = OperationalPhaseModel(
            id=A_UUID,
            operational_profile_id=B_UUID,
            name="Apertura",
            sequence_order=1,
        )
        model = OperationalProfileModel(id=B_UUID, name="Perfil Test")
        model.phases = [phase_model]

        session.execute = AsyncMock(return_value=_mock_scalar_result(model))
        repo = SQLOperationalProfileRepository(session)

        result = await repo.find_by_id(B_UUID)

        assert result is not None
        assert isinstance(result, OperationalProfile)
        assert result.id == B_UUID
        assert result.name == "Perfil Test"
        assert len(result.phases) == 1
        assert result.phases[0].id == A_UUID

    async def test_find_by_id_returns_none(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar_result(None))
        repo = SQLOperationalProfileRepository(session)

        result = await repo.find_by_id(B_UUID)

        assert result is None

    async def test_find_by_id_uses_selectinload(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_scalar_result(None))
        repo = SQLOperationalProfileRepository(session)

        await repo.find_by_id(B_UUID)

        call_stmt = session.execute.call_args[0][0]
        compiled = str(call_stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "operational_profiles" in compiled
        assert B_UUID.hex in compiled

    async def test_save_new_profile(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        phase = OperationalPhase(id=A_UUID, name="Apertura", sequence_order=1)
        profile = OperationalProfile(id=B_UUID, name="Nuevo Perfil", phases=(phase,))

        repo = SQLOperationalProfileRepository(session)

        result = await repo.save(profile)

        assert result.id == B_UUID
        assert result.name == "Nuevo Perfil"
        assert len(result.phases) == 1
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    async def test_save_existing_profile_updates_fields(self) -> None:
        session = AsyncMock()
        existing_model = OperationalProfileModel(id=B_UUID, name="Perfil Original")
        existing_model.phases = []

        session.get = AsyncMock(return_value=existing_model)
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        phase = OperationalPhase(id=A_UUID, name="Apertura", sequence_order=1)
        profile = OperationalProfile(
            id=B_UUID, name="Perfil Actualizado", phases=(phase,)
        )

        repo = SQLOperationalProfileRepository(session)

        result = await repo.save(profile)

        assert existing_model.name == "Perfil Actualizado"
        assert len(existing_model.phases) == 1
        assert existing_model.phases[0].id == A_UUID
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once()

    async def test_save_removes_orphaned_phases(self) -> None:
        session = AsyncMock()
        orphan_phase = OperationalPhaseModel(
            id=C_UUID,
            operational_profile_id=B_UUID,
            name="Antigua",
            sequence_order=1,
        )
        existing_model = OperationalProfileModel(id=B_UUID, name="Perfil")
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

        new_phase = OperationalPhase(id=A_UUID, name="Nueva", sequence_order=1)
        profile = OperationalProfile(id=B_UUID, name="Perfil", phases=(new_phase,))

        repo = SQLOperationalProfileRepository(session)

        result = await repo.save(profile)

        assert len(result.phases) == 1
        assert result.phases[0].id == A_UUID
        session.delete.assert_called_once_with(orphan_phase)

    async def test_save_reuses_mapper(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.add = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        profile = OperationalProfile(
            id=B_UUID,
            name="Perfil Mapper",
            phases=(
                OperationalPhase(id=A_UUID, name="Fase", sequence_order=1),
            ),
        )

        repo = SQLOperationalProfileRepository(session)

        result = await repo.save(profile)

        assert isinstance(result, OperationalProfile)
        assert result.id == B_UUID
