from __future__ import annotations

from src.domain.entities.operational_event import OperationalEvent
from src.infrastructure.persistence.models.operational_event import (
    OperationalEventModel,
)


def operational_event_to_domain(model: OperationalEventModel) -> OperationalEvent:
    return OperationalEvent(
        id=model.id,
        target_zone_id=model.target_zone_id,
        impact_value=model.impact_value,
        is_incident=model.is_incident,
        start_timestamp=model.start_timestamp,
        end_timestamp=model.end_timestamp,
    )


def operational_event_to_model(entity: OperationalEvent) -> OperationalEventModel:
    return OperationalEventModel(
        id=entity.id,
        target_zone_id=entity.target_zone_id,
        impact_value=entity.impact_value,
        is_incident=entity.is_incident,
        start_timestamp=entity.start_timestamp,
        end_timestamp=entity.end_timestamp,
    )
