"""CRUD operations for EventDay."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_day import EventDay
from app.models.operational_profile import OperationalProfile
from app.schemas.event_day import EventDayCreate, EventDayUpdate


async def create(db: AsyncSession, obj_in: EventDayCreate, event_id: str) -> EventDay:
    profile = await db.get(OperationalProfile, obj_in.operational_profile_id)
    if not profile:
        raise ValueError(
            f"OperationalProfile with id '{obj_in.operational_profile_id}' not found"
        )

    if obj_in.operational_end_min <= obj_in.operational_start_min:
        raise ValueError(
            "operational_end_min must be greater than operational_start_min"
        )

    db_obj = EventDay(event_id=event_id, **obj_in.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj


async def get_by_id(db: AsyncSession, id: str) -> EventDay | None:
    return await db.get(EventDay, id)


async def list_by_event(
    db: AsyncSession, event_id: str, skip: int = 0, limit: int = 100,
) -> list[EventDay]:
    result = await db.execute(
        select(EventDay)
        .where(EventDay.event_id == event_id)
        .offset(skip).limit(limit)
        .order_by(EventDay.date)
    )
    return list(result.scalars().all())


async def update(
    db: AsyncSession, db_obj: EventDay, obj_in: EventDayUpdate,
) -> EventDay:
    update_data = obj_in.model_dump(exclude_unset=True)

    if "operational_profile_id" in update_data:
        profile = await db.get(OperationalProfile, update_data["operational_profile_id"])
        if not profile:
            raise ValueError(
                f"OperationalProfile with id '{update_data['operational_profile_id']}' not found"
            )

    if "operational_start_min" in update_data or "operational_end_min" in update_data:
        new_start = update_data.get("operational_start_min", db_obj.operational_start_min)
        new_end = update_data.get("operational_end_min", db_obj.operational_end_min)
        if new_end <= new_start:
            raise ValueError(
                "operational_end_min must be greater than operational_start_min"
            )

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    await db.flush()
    await db.refresh(db_obj)
    return db_obj


async def delete(db: AsyncSession, id: str) -> bool:
    db_obj = await db.get(EventDay, id)
    if not db_obj:
        return False
    await db.delete(db_obj)
    await db.flush()
    return True
