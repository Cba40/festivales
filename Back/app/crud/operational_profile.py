"""CRUD operations for OperationalProfile."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operational_profile import OperationalProfile
from app.schemas.operational_profile import OperationalProfileCreate, OperationalProfileUpdate


async def create(db: AsyncSession, obj_in: OperationalProfileCreate) -> OperationalProfile:
    result = await db.execute(
        select(OperationalProfile).where(OperationalProfile.name == obj_in.name)
    )
    if result.scalar_one_or_none():
        raise ValueError(f"OperationalProfile with name '{obj_in.name}' already exists")

    db_obj = OperationalProfile(name=obj_in.name, description=obj_in.description)
    db.add(db_obj)
    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get_by_id(db: AsyncSession, id: UUID) -> OperationalProfile | None:
    return await db.get(OperationalProfile, id)


async def list_profiles(
    db: AsyncSession, skip: int = 0, limit: int = 100,
) -> list[OperationalProfile]:
    result = await db.execute(
        select(OperationalProfile)
        .offset(skip).limit(limit)
        .order_by(OperationalProfile.name)
    )
    return list(result.scalars().all())


async def update(
    db: AsyncSession, db_obj: OperationalProfile, obj_in: OperationalProfileUpdate,
) -> OperationalProfile:
    update_data = obj_in.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] != db_obj.name:
        result = await db.execute(
            select(OperationalProfile).where(OperationalProfile.name == update_data["name"])
        )
        if result.scalar_one_or_none():
            raise ValueError(f"OperationalProfile with name '{update_data['name']}' already exists")

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete(db: AsyncSession, id: UUID) -> bool:
    db_obj = await db.get(OperationalProfile, id)
    if not db_obj:
        return False
    await db.delete(db_obj)
    await db.flush()
    await db.commit()
    return True
