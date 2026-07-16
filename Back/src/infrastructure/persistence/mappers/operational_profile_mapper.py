from __future__ import annotations

from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.operational_profile import OperationalProfile
from src.infrastructure.persistence.models.operational_phase import (
    OperationalPhaseModel,
)
from src.infrastructure.persistence.models.operational_profile import (
    OperationalProfileModel,
)


def operational_profile_to_domain(model: OperationalProfileModel) -> OperationalProfile:
    phases = tuple(
        OperationalPhase(
            id=phase_model.id,
            name=phase_model.name,
            sequence_order=phase_model.sequence_order,
        )
        for phase_model in model.phases
    )
    return OperationalProfile(id=model.id, name=model.name, phases=phases)


def operational_profile_to_model(entity: OperationalProfile) -> OperationalProfileModel:
    model = OperationalProfileModel(id=entity.id, name=entity.name)
    model.phases = [
        OperationalPhaseModel(
            id=phase.id,
            name=phase.name,
            sequence_order=phase.sequence_order,
            operational_profile_id=entity.id,
        )
        for phase in entity.phases
    ]
    return model
