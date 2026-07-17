from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.operational_profile import OperationalProfile
from src.domain.entities.zone_behavior import FlowRestriction, ZoneBehavior
from src.infrastructure.persistence.models.zone_behavior import ZoneBehaviorModel
from src.infrastructure.persistence.repositories import (
    SQLOperationalProfileRepository,
)


async def seed_operational_profile(
    session: AsyncSession,
    profile_name: str,
    phases: list[tuple[str, int]],
    zone_behavior_config: dict[UUID, dict[int, tuple[float, FlowRestriction]]],
) -> OperationalProfile:
    repo = SQLOperationalProfileRepository(session)

    phase_entities = tuple(
        OperationalPhase(id=uuid4(), name=name, sequence_order=order)
        for name, order in phases
    )

    profile = OperationalProfile(
        id=uuid4(),
        name=profile_name,
        phases=phase_entities,
    )
    profile = await repo.save(profile)

    for phase in phase_entities:
        for zone_type_id, phase_config in zone_behavior_config.items():
            if phase.sequence_order not in phase_config:
                continue
            density, restriction = phase_config[phase.sequence_order]
            zone_behavior = ZoneBehavior(
                id=uuid4(),
                zone_type_id=zone_type_id,
                operational_phase_id=phase.id,
                density_factor=density,
                flow_restriction=restriction,
            )
            model = ZoneBehaviorModel(
                id=zone_behavior.id,
                zone_type_id=zone_behavior.zone_type_id,
                operational_phase_id=zone_behavior.operational_phase_id,
                density_factor=zone_behavior.density_factor,
                flow_restriction=zone_behavior.flow_restriction,
            )
            session.add(model)

    await session.flush()
    return profile
