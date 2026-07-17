from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.zone_type import ZoneType
from src.infrastructure.persistence.models.zone_type import ZoneTypeModel

ZONE_TYPE_NAMES: list[str] = [
    "Parking",
    "Gastronomy",
    "Sanitary",
    "Transport",
    "Accommodation",
    "Security",
    "Information",
    "RestArea",
]


async def seed_zone_types(session: AsyncSession) -> list[ZoneType]:
    result = await session.execute(select(ZoneTypeModel.name))
    existing_names = {row[0] for row in result.fetchall()}

    created: list[ZoneType] = []
    for name in ZONE_TYPE_NAMES:
        if name in existing_names:
            continue
        zone_type = ZoneType(id=uuid4(), name=name)
        model = ZoneTypeModel(id=zone_type.id, name=zone_type.name)
        session.add(model)
        created.append(zone_type)

    if created:
        await session.flush()
    return created
