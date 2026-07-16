from __future__ import annotations

from src.domain.entities.zone_type import ZoneType
from src.infrastructure.persistence.models.zone_type import ZoneTypeModel


def zone_type_to_domain(model: ZoneTypeModel) -> ZoneType:
    return ZoneType(id=model.id, name=model.name)


def zone_type_to_model(entity: ZoneType) -> ZoneTypeModel:
    return ZoneTypeModel(id=entity.id, name=entity.name)
