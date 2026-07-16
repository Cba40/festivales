from __future__ import annotations

from src.domain.entities.zone import Zone
from src.infrastructure.persistence.models.zone import ZoneModel


def zone_to_domain(model: ZoneModel) -> Zone:
    return Zone(
        id=model.id,
        name=model.name,
        zone_type_id=model.zone_type_id,
        capacity=model.capacity,
    )


def zone_to_model(entity: Zone) -> ZoneModel:
    return ZoneModel(
        id=entity.id,
        name=entity.name,
        zone_type_id=entity.zone_type_id,
        capacity=entity.capacity,
    )
