from __future__ import annotations

from src.domain.entities.event_day_phase import EventDayPhase
from src.infrastructure.persistence.models.event_day_phase import EventDayPhaseModel


def event_day_phase_to_domain(model: EventDayPhaseModel) -> EventDayPhase:
    return EventDayPhase(
        id=model.id,
        event_day_id=model.event_day_id,
        operational_phase_id=model.operational_phase_id,
        start_min=model.start_min,
        end_min=model.end_min,
    )


def event_day_phase_to_model(entity: EventDayPhase) -> EventDayPhaseModel:
    return EventDayPhaseModel(
        id=entity.id,
        event_day_id=entity.event_day_id,
        operational_phase_id=entity.operational_phase_id,
        start_min=entity.start_min,
        end_min=entity.end_min,
    )
