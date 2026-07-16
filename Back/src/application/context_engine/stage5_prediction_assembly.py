from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState


def assemble_prediction(
    zone_states: Sequence[ZoneState],
    active_operational_phase: OperationalPhase,
    active_event_day_phase: EventDayPhase,
    timestamp: datetime,
) -> TerritorialPrediction:
    return TerritorialPrediction(
        timestamp=timestamp,
        zone_states=list(zone_states),
        active_phase_id=active_operational_phase.id,
        active_event_day_phase_id=active_event_day_phase.id,
    )
