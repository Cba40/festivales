from __future__ import annotations

from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.infrastructure.persistence.models.event_day import EventDayModel
from src.infrastructure.persistence.models.event_day_phase import EventDayPhaseModel


def event_day_to_domain(model: EventDayModel) -> EventDay:
    phases = tuple(
        EventDayPhase(
            id=phase_model.id,
            event_day_id=phase_model.event_day_id,
            operational_phase_id=phase_model.operational_phase_id,
            start_min=phase_model.start_min,
            end_min=phase_model.end_min,
        )
        for phase_model in model.phases
    )
    return EventDay(
        id=model.id,
        event_date=model.event_date,
        operational_profile_id=model.operational_profile_id,
        attendance_level_id=model.attendance_level_id,
        operational_start_min=model.operational_start_min,
        operational_end_min=model.operational_end_min,
        phases=phases,
    )


def event_day_to_model(entity: EventDay) -> EventDayModel:
    model = EventDayModel(
        id=entity.id,
        event_date=entity.event_date,
        operational_profile_id=entity.operational_profile_id,
        attendance_level_id=entity.attendance_level_id,
        operational_start_min=entity.operational_start_min,
        operational_end_min=entity.operational_end_min,
    )
    model.phases = [
        EventDayPhaseModel(
            id=phase.id,
            event_day_id=entity.id,
            operational_phase_id=phase.operational_phase_id,
            start_min=phase.start_min,
            end_min=phase.end_min,
        )
        for phase in entity.phases
    ]
    return model
