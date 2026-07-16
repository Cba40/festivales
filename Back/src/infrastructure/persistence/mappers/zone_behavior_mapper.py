from __future__ import annotations

from src.domain.entities.zone_behavior import ZoneBehavior
from src.infrastructure.persistence.models.zone_behavior import ZoneBehaviorModel


def zone_behavior_to_domain(model: ZoneBehaviorModel) -> ZoneBehavior:
    return ZoneBehavior(
        id=model.id,
        zone_type_id=model.zone_type_id,
        operational_phase_id=model.operational_phase_id,
        density_factor=model.density_factor,
        flow_restriction=model.flow_restriction,
    )


def zone_behavior_to_model(entity: ZoneBehavior) -> ZoneBehaviorModel:
    return ZoneBehaviorModel(
        id=entity.id,
        zone_type_id=entity.zone_type_id,
        operational_phase_id=entity.operational_phase_id,
        density_factor=entity.density_factor,
        flow_restriction=entity.flow_restriction,
    )
