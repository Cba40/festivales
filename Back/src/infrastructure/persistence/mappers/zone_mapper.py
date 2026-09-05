from __future__ import annotations

from src.domain.entities.zone import Zone
from src.infrastructure.persistence.models.zone import ZoneModel


def zone_to_domain(model: ZoneModel) -> Zone:
    return Zone(
        id=model.id,
        name=model.name,
        zone_type_id=None,  # Not in root chain schema
        capacity=model.capacity,
        type=model.type,
        subtipo=None,  # Root chain has 'type' and 'saturation'/'status', not subtipo in same way
        available_capacity=model.available_capacity,
    )


def zone_to_model(entity: Zone) -> ZoneModel:
    return ZoneModel(
        id=entity.id,
        name=entity.name,
        # zone_type_id not in root chain schema
        capacity=entity.capacity,
        # type, saturation, status, etc. would need to be set
    )
