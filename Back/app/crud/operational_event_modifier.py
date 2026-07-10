"""CRUD operations for OperationalEventModifier."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operational_event_modifier import OperationalEventModifier
from app.models.zone_type import ZoneType
from app.schemas.operational_event_modifier import (
    OperationalEventModifierCreate,
    OperationalEventModifierUpdate,
)


async def create(
    db: AsyncSession, obj_in: OperationalEventModifierCreate,
) -> OperationalEventModifier:
    if obj_in.zone_type_id is not None:
        zone_type = await db.get(ZoneType, obj_in.zone_type_id)
        if not zone_type:
            raise ValueError(f"ZoneType with id '{obj_in.zone_type_id}' not found")

    result = await db.execute(
        select(OperationalEventModifier).where(
            OperationalEventModifier.event_type == obj_in.event_type,
            OperationalEventModifier.zone_type_id == obj_in.zone_type_id,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError(
            f"OperationalEventModifier already exists for event_type "
            f"'{obj_in.event_type}' and zone_type_id '{obj_in.zone_type_id}'"
        )

    db_obj = OperationalEventModifier(**obj_in.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj


async def get_by_id(db: AsyncSession, id: UUID) -> OperationalEventModifier | None:
    return await db.get(OperationalEventModifier, id)


async def list_by_event_type(
    db: AsyncSession, event_type: str,
) -> list[OperationalEventModifier]:
    result = await db.execute(
        select(OperationalEventModifier)
        .where(OperationalEventModifier.event_type == event_type)
    )
    return list(result.scalars().all())


async def update(
    db: AsyncSession, db_obj: OperationalEventModifier, obj_in: OperationalEventModifierUpdate,
) -> OperationalEventModifier:
    update_data = obj_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    await db.flush()
    await db.refresh(db_obj)
    return db_obj


async def delete(db: AsyncSession, id: UUID) -> bool:
    db_obj = await db.get(OperationalEventModifier, id)
    if not db_obj:
        return False
    await db.delete(db_obj)
    await db.flush()
    return True
