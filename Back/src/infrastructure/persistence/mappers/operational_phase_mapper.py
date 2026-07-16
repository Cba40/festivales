from __future__ import annotations

from src.domain.entities.operational_phase import OperationalPhase
from src.infrastructure.persistence.models.operational_phase import (
    OperationalPhaseModel,
)


def operational_phase_to_domain(model: OperationalPhaseModel) -> OperationalPhase:
    return OperationalPhase(
        id=model.id,
        name=model.name,
        sequence_order=model.sequence_order,
    )


def operational_phase_to_model(entity: OperationalPhase) -> OperationalPhaseModel:
    return OperationalPhaseModel(
        id=entity.id,
        name=entity.name,
        sequence_order=entity.sequence_order,
    )
