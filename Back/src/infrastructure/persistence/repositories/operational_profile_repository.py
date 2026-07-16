from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.operational_profile import OperationalProfile
from src.domain.ports.operational_profile_repository import (
    OperationalProfileRepository,
)
from src.infrastructure.persistence.mappers import (
    operational_profile_to_domain,
    operational_profile_to_model,
)
from src.infrastructure.persistence.models import (
    OperationalPhaseModel,
    OperationalProfileModel,
)


class SQLOperationalProfileRepository(OperationalProfileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, profile_id: UUID) -> OperationalProfile | None:
        stmt = (
            select(OperationalProfileModel)
            .where(OperationalProfileModel.id == profile_id)
            .options(selectinload(OperationalProfileModel.phases))
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return operational_profile_to_domain(model)

    async def save(self, profile: OperationalProfile) -> OperationalProfile:
        existing = await self._session.get(
            OperationalProfileModel,
            profile.id,
            options=[selectinload(OperationalProfileModel.phases)],
        )

        if existing is not None:
            existing.name = profile.name

            existing_phase_ids = {p.id for p in existing.phases}
            new_phase_ids = {p.id for p in profile.phases}

            orphan_ids = existing_phase_ids - new_phase_ids
            if orphan_ids:
                existing.phases[:] = [
                    p for p in existing.phases if p.id not in orphan_ids
                ]
                for phase_id in orphan_ids:
                    orphan = await self._session.get(OperationalPhaseModel, phase_id)
                    if orphan is not None:
                        await self._session.delete(orphan)

            for phase in profile.phases:
                if phase.id in existing_phase_ids:
                    phase_model = next(
                        p for p in existing.phases if p.id == phase.id
                    )
                    phase_model.name = phase.name
                    phase_model.sequence_order = phase.sequence_order
                else:
                    existing.phases.append(
                        OperationalPhaseModel(
                            id=phase.id,
                            operational_profile_id=profile.id,
                            name=phase.name,
                            sequence_order=phase.sequence_order,
                        )
                    )

            await self._session.flush()
            await self._session.refresh(existing, attribute_names=["phases"])
            return operational_profile_to_domain(existing)
        else:
            model = operational_profile_to_model(profile)
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model, attribute_names=["phases"])
            return operational_profile_to_domain(model)
