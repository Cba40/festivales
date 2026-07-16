from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone_behavior import FlowRestriction


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


class ZoneApplication:
    def __init__(
        self,
        zone_id: UUID,
        projected_density: int,
        active_restriction: FlowRestriction,
    ) -> None:
        self._zone_id = zone_id
        self._projected_density = projected_density
        self._active_restriction = active_restriction

    @property
    def zone_id(self) -> UUID:
        return self._zone_id

    @property
    def projected_density(self) -> int:
        return self._projected_density

    @property
    def active_restriction(self) -> FlowRestriction:
        return self._active_restriction

    def __repr__(self) -> str:
        return (
            f"ZoneApplication("
            f"zone_id={self._zone_id!r}, "
            f"projected_density={self._projected_density!r}, "
            f"active_restriction={self._active_restriction!r})"
        )


class ZoneBehaviorApplicationResult:
    def __init__(
        self,
        active_operational_phase: OperationalPhase,
        active_event_day_phase: EventDayPhase,
        timestamp: datetime,
        zone_applications: Mapping[UUID, ZoneApplication],
    ) -> None:
        self._active_operational_phase = active_operational_phase
        self._active_event_day_phase = active_event_day_phase
        self._timestamp = timestamp
        self._zone_applications = dict(zone_applications)

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
    def zone_applications(self) -> Mapping[UUID, ZoneApplication]:
        return dict(self._zone_applications)

    def __repr__(self) -> str:
        return (
            f"ZoneBehaviorApplicationResult("
            f"active_operational_phase={self._active_operational_phase!r}, "
            f"active_event_day_phase={self._active_event_day_phase!r}, "
            f"timestamp={self._timestamp!r}, "
            f"zone_applications_count={len(self._zone_applications)})"
        )
