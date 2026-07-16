from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from src.application.context_engine.dto import EventEvaluationResult
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_event import OperationalEvent
from src.domain.entities.operational_phase import OperationalPhase


def apply_dynamic_events(
    active_operational_phase: OperationalPhase,
    active_event_day_phase: EventDayPhase,
    events: Sequence[OperationalEvent],
    timestamp: datetime,
) -> EventEvaluationResult:
    impacts: dict[UUID, int] = {}

    for event in events:
        if not (event.start_timestamp <= timestamp < event.end_timestamp):
            continue
        current = impacts.get(event.target_zone_id, 0)
        current += event.impact_value
        if current < -100:
            current = -100
        impacts[event.target_zone_id] = current

    return EventEvaluationResult(
        active_operational_phase=active_operational_phase,
        active_event_day_phase=active_event_day_phase,
        timestamp=timestamp,
        event_impacts=impacts,
    )
