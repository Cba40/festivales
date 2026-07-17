from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.entities.zone_type import ZoneType
from src.infrastructure.persistence.models.attendance_level import (
    AttendanceLevelModel,
)
from src.infrastructure.persistence.models.zone_type import ZoneTypeModel
from src.infrastructure.seeds.attendance_levels_seed import seed_attendance_levels
from src.infrastructure.seeds.event_day_seed import seed_event_day
from src.infrastructure.seeds.operational_profile_seed import seed_operational_profile
from src.infrastructure.seeds.zone_types_seed import ZONE_TYPE_NAMES, seed_zone_types


A_UUID = UUID("11111111-1111-1111-1111-111111111111")
B_UUID = UUID("22222222-2222-2222-2222-222222222222")


def _mock_fetchall_result(rows: list[tuple]) -> MagicMock:
    result = MagicMock()
    result.fetchall = MagicMock(return_value=rows)
    return result


class TestSeedZoneTypes:
    async def test_creates_all_8_zone_types_when_empty(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_fetchall_result([]))
        session.add = MagicMock()
        session.flush = AsyncMock()

        result = await seed_zone_types(session)

        assert len(result) == 8
        for zone_type in result:
            assert isinstance(zone_type, ZoneType)
            assert zone_type.name in ZONE_TYPE_NAMES
        assert session.add.call_count == 8
        session.flush.assert_awaited_once()

    async def test_is_idempotent_when_all_exist(self) -> None:
        session = AsyncMock()
        existing_names = [(name,) for name in ZONE_TYPE_NAMES]
        session.execute = AsyncMock(return_value=_mock_fetchall_result(existing_names))
        session.add = MagicMock()
        session.flush = AsyncMock()

        result = await seed_zone_types(session)

        assert len(result) == 0
        session.add.assert_not_called()
        session.flush.assert_not_called()

    async def test_creates_only_missing_zone_types(self) -> None:
        session = AsyncMock()
        partial_names = [("Parking",), ("Gastronomy",)]
        session.execute = AsyncMock(return_value=_mock_fetchall_result(partial_names))
        session.add = MagicMock()
        session.flush = AsyncMock()

        result = await seed_zone_types(session)

        assert len(result) == 6
        created_names = {zt.name for zt in result}
        assert "Parking" not in created_names
        assert "Gastronomy" not in created_names
        assert "Sanitary" in created_names
        assert session.add.call_count == 6
        session.flush.assert_awaited_once()

    async def test_all_zone_type_names_match_p30_spec(self) -> None:
        expected = [
            "Parking",
            "Gastronomy",
            "Sanitary",
            "Transport",
            "Accommodation",
            "Security",
            "Information",
            "RestArea",
        ]
        assert ZONE_TYPE_NAMES == expected


class TestSeedAttendanceLevels:
    async def test_creates_all_3_levels_when_empty(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_fetchall_result([]))
        session.add = MagicMock()
        session.flush = AsyncMock()

        multipliers = {"Bajo": 0.5, "Medio": 1.0, "Alto": 1.5}
        result = await seed_attendance_levels(session, multipliers=multipliers)

        assert len(result) == 3
        for level in result:
            assert isinstance(level, AttendanceLevel)
            assert level.name in multipliers
            assert level.multiplier == multipliers[level.name]
        assert session.add.call_count == 3
        session.flush.assert_awaited_once()

    async def test_is_idempotent_when_all_exist(self) -> None:
        session = AsyncMock()
        multipliers = {"Bajo": 0.5, "Medio": 1.0, "Alto": 1.5}
        existing_names = [(name,) for name in multipliers]
        session.execute = AsyncMock(return_value=_mock_fetchall_result(existing_names))
        session.add = MagicMock()
        session.flush = AsyncMock()

        result = await seed_attendance_levels(session, multipliers=multipliers)

        assert len(result) == 0
        session.add.assert_not_called()
        session.flush.assert_not_called()

    async def test_accepts_custom_multipliers(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_mock_fetchall_result([]))
        session.add = MagicMock()
        session.flush = AsyncMock()

        custom = {"Bajo": 0.3, "Medio": 0.8, "Alto": 1.8}
        result = await seed_attendance_levels(session, multipliers=custom)

        assert len(result) == 3
        for level in result:
            assert level.multiplier == custom[level.name]

    async def test_multipliers_parameter_is_required(self) -> None:
        with pytest.raises(TypeError):
            await seed_attendance_levels(AsyncMock())


class TestSeedOperationalProfile:
    async def test_creates_profile_and_behaviors_when_empty(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.add = MagicMock()
        session.flush = AsyncMock()

        zone_type_id_a = UUID("11111111-1111-1111-1111-111111111111")
        zone_type_id_b = UUID("22222222-2222-2222-2222-222222222222")

        phases = [("Apertura / Ingreso", 1), ("Pico Operativo", 2), ("Cierre / Salida", 3)]
        behavior_config = {
            zone_type_id_a: {
                1: (0.85, FlowRestriction.REGULATED),
                2: (0.80, FlowRestriction.REGULATED),
                3: (0.70, FlowRestriction.REGULATED),
            },
            zone_type_id_b: {
                1: (0.75, FlowRestriction.OPEN),
                2: (0.60, FlowRestriction.REGULATED),
                3: (0.50, FlowRestriction.OPEN),
            },
        }

        result = await seed_operational_profile(
            session,
            profile_name="Perfil Estándar de Evento Masivo",
            phases=phases,
            zone_behavior_config=behavior_config,
        )

        assert result is not None
        assert result.name == "Perfil Estándar de Evento Masivo"
        assert len(result.phases) == 3
        assert session.add.call_count == 7
        assert session.flush.await_count == 2


class TestSeedEventDay:
    async def test_creates_event_day_with_given_data(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)
        session.add = MagicMock()
        session.flush = AsyncMock()

        event_date = date(2026, 1, 10)
        profile_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        level_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        phases = [
            (UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"), 1200, 1380),
            (UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"), 1380, 1500),
            (UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"), 1500, 1680),
        ]

        result = await seed_event_day(
            session,
            event_date=event_date,
            operational_profile_id=profile_id,
            attendance_level_id=level_id,
            operational_start_min=1200,
            operational_end_min=1680,
            phases=phases,
        )

        assert result is not None
        assert result.event_date == event_date
        assert result.operational_profile_id == profile_id
        assert result.attendance_level_id == level_id
        assert result.operational_start_min == 1200
        assert result.operational_end_min == 1680
        assert len(result.phases) == 3

    async def test_requires_all_parameters(self) -> None:
        with pytest.raises(TypeError):
            await seed_event_day(AsyncMock())
