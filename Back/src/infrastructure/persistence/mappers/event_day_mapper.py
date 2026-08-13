from __future__ import annotations

from uuid import UUID

from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.infrastructure.persistence.models.event_day import EventDayModel
from src.infrastructure.persistence.models.event_day_phase import EventDayPhaseModel


def _to_uuid_or_none(value: str | UUID | None) -> UUID | None:
    """Normaliza un id varchar (o ya UUID) de la capa ORM a UUID de dominio.

    La columna event_days.attendance_level_id es varchar(36); el dominio
    EventDay exige UUID. La conversión ocurre en la frontera ORM -> dominio.
    """
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(value)


def event_day_to_domain(model: EventDayModel) -> EventDay:
    phases = tuple(
        EventDayPhase(
            id=phase_model.id,
            event_day_id=phase_model.event_day_id,
            operational_phase_id=phase_model.operational_phase_id,
            start_min=phase_model.start_min,
            end_min=phase_model.end_min,
            intensity=phase_model.intensity,
        )
        for phase_model in model.phases
    )
    return EventDay(
        id=model.id,
        event_date=model.event_date,
        operational_profile_id=model.operational_profile_id,
        attendance_level_id=_to_uuid_or_none(model.attendance_level_id),
        operational_start_min=model.operational_start_min,
        operational_end_min=model.operational_end_min,
        estimated_vehicles=model.estimated_vehicles,
        average_parking_duration=model.average_parking_duration,
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
        estimated_vehicles=entity.estimated_vehicles,
        average_parking_duration=entity.average_parking_duration,
    )
    model.phases = [
        EventDayPhaseModel(
            id=phase.id,
            event_day_id=entity.id,
            operational_phase_id=phase.operational_phase_id,
            start_min=phase.start_min,
            end_min=phase.end_min,
            intensity=phase.intensity,
        )
        for phase in entity.phases
    ]
    return model
