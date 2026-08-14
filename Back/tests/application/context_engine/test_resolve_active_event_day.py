"""Corrección temporal — resolve_active_event_day.

Verifica la selección de la jornada activa por ventana operativa, soportando
jornadas que cruzan medianoche (minutos >= 1440 desde la medianoche de la
fecha civil) y el uso de la fecha LOCAL (Argentina) en lugar de UTC.

Sin base de datos: el repositorio se simula con un dict de fechas civiles.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Callable
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from src.application.context_engine.stage1_context_resolution import (
    resolve_active_event_day,
)
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase

AR = ZoneInfo("America/Argentina/Buenos_Aires")

PROFILE_ID = UUID("99999999-0000-0000-0000-000000000001")
DAY_ID = UUID("00000000-0000-0000-0000-000000000001")
PHASE_ID = UUID("00000000-0000-0000-0000-000000000002")


def _day(day: int, start_min: int, end_min: int) -> EventDay:
    return EventDay(
        id=DAY_ID,
        event_date=date(2026, 8, day),
        operational_profile_id=PROFILE_ID,
        operational_start_min=start_min,
        operational_end_min=end_min,
        phases=(
            EventDayPhase(
                id=PHASE_ID,
                event_day_id=DAY_ID,
                operational_phase_id=UUID(
                    "00000000-0000-0000-0000-000000000003"
                ),
                start_min=start_min,
                end_min=end_min,
                intensity=0.5,
            ),
        ),
    )


class FakeEventDayRepo:
    def __init__(self, days: dict[date, EventDay]) -> None:
        self._days = days
        self.lookups: list[date] = []

    async def find_by_date(self, target_date: date) -> EventDay | None:
        self.lookups.append(target_date)
        return self._days.get(target_date)


async def _resolve(
    days: dict[date, EventDay],
    timestamp: datetime,
) -> tuple[EventDay | None, list[date]]:
    repo = FakeEventDayRepo(days)
    result = await resolve_active_event_day(timestamp, repo.find_by_date)
    return result, repo.lookups


def _ar(day: int, hour: int, minute: int) -> datetime:
    return datetime(2026, 8, day, hour, minute, tzinfo=AR)


def _utc(day: int, hour: int, minute: int) -> datetime:
    return datetime(2026, 8, day, hour, minute, tzinfo=timezone.utc)


class TestNormalDay:
    """Jornada diurna [1080, 1440) = 18:00-23:59 inclusive."""

    DAY = _day(14, 1080, 1440)

    async def test_active_at_21_45(self) -> None:
        result, lookups = await _resolve({date(2026, 8, 14): self.DAY}, _ar(14, 21, 45))
        assert result is self.DAY
        assert lookups == [date(2026, 8, 14)]

    async def test_active_at_23_59(self) -> None:
        result, _ = await _resolve({date(2026, 8, 14): self.DAY}, _ar(14, 23, 59))
        assert result is self.DAY

    async def test_inactive_at_00_00(self) -> None:
        result, lookups = await _resolve({date(2026, 8, 14): self.DAY}, _ar(15, 0, 0))
        assert result is None
        assert lookups == [date(2026, 8, 15), date(2026, 8, 14)]

    async def test_inactive_outside_window(self) -> None:
        result, _ = await _resolve({date(2026, 8, 14): self.DAY}, _ar(14, 10, 0))
        assert result is None


class TestNightlyCrossMidnight:
    """Jornada nocturna [1200, 1680) = 20:00 -> 04:00 del día siguiente."""

    DAY = _day(14, 1200, 1680)

    @pytest.mark.parametrize(
        "hour,minute",
        [(20, 0), (21, 45), (23, 59)],
    )
    async def test_active_on_start_date(self, hour: int, minute: int) -> None:
        result, _ = await _resolve(
            {date(2026, 8, 14): self.DAY}, _ar(14, hour, minute)
        )
        assert result is self.DAY

    @pytest.mark.parametrize(
        "hour,minute",
        [(0, 0), (0, 1), (1, 0), (3, 59)],
    )
    async def test_active_after_midnight_via_previous_day(
        self, hour: int, minute: int
    ) -> None:
        result, lookups = await _resolve(
            {date(2026, 8, 14): self.DAY}, _ar(15, hour, minute)
        )
        assert result is self.DAY
        assert lookups == [date(2026, 8, 15), date(2026, 8, 14)]

    @pytest.mark.parametrize(
        "hour,minute",
        [(4, 0), (4, 1)],
    )
    async def test_inactive_after_window_ends(self, hour: int, minute: int) -> None:
        result, _ = await _resolve(
            {date(2026, 8, 14): self.DAY}, _ar(15, hour, minute)
        )
        assert result is None


class TestConsecutiveDays:
    """ED14 nocturna [1200, 1680); ED15 diurna [1080, 1380)."""

    ED14 = _day(14, 1200, 1680)
    ED15 = _day(15, 1080, 1380)
    DAYS = {
        date(2026, 8, 14): ED14,
        date(2026, 8, 15): ED15,
    }

    async def test_before_midnight_selects_start_date(self) -> None:
        result, _ = await _resolve(self.DAYS, _ar(14, 21, 45))
        assert result is self.ED14

    async def test_after_midnight_stays_on_night_day(self) -> None:
        result, lookups = await _resolve(self.DAYS, _ar(15, 1, 0))
        assert result is self.ED14
        assert lookups == [date(2026, 8, 15), date(2026, 8, 14)]

    async def test_gap_between_nights_returns_none(self) -> None:
        result, _ = await _resolve(self.DAYS, _ar(15, 4, 1))
        assert result is None

    async def test_next_day_window_selects_next_day(self) -> None:
        result, _ = await _resolve(self.DAYS, _ar(15, 18, 0))
        assert result is self.ED15


class TestUtcDateRegression:
    """El bug original: se seleccionaba por fecha UTC (día siguiente entre
    21:00-23:59 AR). La resolución debe usar la fecha LOCAL."""

    NIGHT14 = _day(14, 1200, 1680)   # 20:00-04:00 del 14/08
    DAY15 = _day(15, 0, 1200)        # 00:00-20:00 del 15/08
    DAYS = {
        date(2026, 8, 14): NIGHT14,
        date(2026, 8, 15): DAY15,
    }

    async def test_local_date_is_used_not_utc(self) -> None:
        # UTC 15/08 00:41 == AR 14/08 21:41: debe resolver a NIGHT14.
        # El código viejo (fecha UTC 15/08) habría resuelto a DAY15.
        result, lookups = await _resolve(self.DAYS, _utc(15, 0, 41))
        assert result is self.NIGHT14
        assert lookups[0] == date(2026, 8, 14)

    async def test_no_configured_local_day_returns_none(self) -> None:
        # Solo existe DAY15; a AR 14/08 21:41 no hay jornada configurada.
        # El código viejo habría devuelto DAY15 (jornada que aún no comienza).
        days = {date(2026, 8, 15): self.DAY15}
        result, _ = await _resolve(days, _utc(15, 0, 41))
        assert result is None