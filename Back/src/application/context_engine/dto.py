from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase


class EventEvaluationResult:
    def __init__(
        self,
        active_operational_phase: OperationalPhase,
        active_event_day_phase: EventDayPhase,
        timestamp: datetime,
        event_impacts: Mapping[UUID, int],
    ) -> None:
        self._active_operational_phase = active_operational_phase
        self._active_event_day_phase = active_event_day_phase
        self._timestamp = timestamp
        self._event_impacts = dict(event_impacts)

    @property
    def active_operational_phase(self) -> OperationalPhase:
        return self._active_operational_phase

    @property
    def active_event_day_phase(self) -> EventDayPhase:
        return self._active_event_day_phase

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def event_impacts(self) -> Mapping[UUID, int]:
        return dict(self._event_impacts)

    def __repr__(self) -> str:
        return (
            f"EventEvaluationResult("
            f"active_operational_phase={self._active_operational_phase!r}, "
            f"active_event_day_phase={self._active_event_day_phase!r}, "
            f"timestamp={self._timestamp!r}, "
            f"event_impacts={self._event_impacts!r})"
        )
