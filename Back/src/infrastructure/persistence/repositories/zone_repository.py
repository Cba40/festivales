from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.zone import Zone
from src.domain.ports.zone_repository import ZoneRepository
from src.infrastructure.persistence.mappers import zone_to_domain, zone_to_model
from src.infrastructure.persistence.models import ZoneModel


class SQLZoneRepository(ZoneRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, zone_id: UUID) -> Zone | None:
        stmt = select(ZoneModel).where(ZoneModel.id == zone_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return zone_to_domain(model)

    async def save(self, zone: Zone) -> Zone:
        existing = await self._session.get(ZoneModel, zone.id)

        if existing is not None:
            existing.name = zone.name
            existing.zone_type_id = zone.zone_type_id
            existing.capacity = zone.capacity

            await self._session.flush()
            await self._session.refresh(existing)
            return zone_to_domain(existing)
        else:
            model = zone_to_model(zone)
            self._session.add(model)
            await self._session.flush()
            await self._session.refresh(model)
            return zone_to_domain(model)
