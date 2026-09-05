from __future__ import annotations

from src.domain.entities.operational_observation import OperationalObservation
from src.infrastructure.persistence.models.operational_observation import (
    OperationalObservationModel,
)


def operational_observation_to_domain(model: OperationalObservationModel) -> OperationalObservation:
    return OperationalObservation(
        id=model.id,
        event_day_id=model.event_day_id,
        zone_id=model.zone_id,
        timestamp=model.timestamp,
        observed_density=model.observed_density,
        observer_id=model.observer_id,
        source=model.source,
        metadata=model.meta,
        created_at=model.created_at,
    )


def operational_observation_to_model(entity: OperationalObservation) -> OperationalObservationModel:
    return OperationalObservationModel(
        id=entity.id,
        event_day_id=entity.event_day_id,
        zone_id=entity.zone_id,
        timestamp=entity.timestamp,
        observed_density=entity.observed_density,
        observer_id=entity.observer_id,
        source=entity.source,
        meta=entity.metadata,
    )