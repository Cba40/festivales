from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from src.application.context_engine.exceptions import InvalidPhaseContext
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase

LOCAL_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def _to_current_min(event_date: date, timestamp: datetime) -> int:
    local_ts = timestamp.astimezone(LOCAL_TZ)
    days_diff = (local_ts.date() - event_date).days
    return days_diff * 1440 + local_ts.hour * 60 + local_ts.minute


def resolve_contextual_phase(
    event_day: EventDay,
    operational_phases: Mapping[UUID, OperationalPhase],
    timestamp: datetime,
) -> tuple[EventDayPhase, OperationalPhase]:
    current_min = _to_current_min(event_day.event_date, timestamp)

    if not event_day.phases:
        raise InvalidPhaseContext(
            f"EventDay {event_day.id} has no phases"
        )

    for ed_phase in event_day.phases:
        if ed_phase.start_min <= current_min < ed_phase.end_min:
            try:
                op_phase = operational_phases[ed_phase.operational_phase_id]
            except KeyError:
                raise InvalidPhaseContext(
                    f"OperationalPhase {ed_phase.operational_phase_id} "
                    f"not found in operational phases index"
                )
            return ed_phase, op_phase

    raise InvalidPhaseContext(
        f"No EventDayPhase contains minute {current_min} "
        f"for EventDay {event_day.id}"
    )
