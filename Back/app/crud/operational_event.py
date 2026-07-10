"""CRUD operations for OperationalEvent."""
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_day import EventDay
from app.models.operational_event import OperationalEvent
from app.schemas.operational_event import OperationalEventCreate, OperationalEventUpdate


async def create(db: AsyncSession, obj_in: OperationalEventCreate) -> OperationalEvent:
    event_day = await db.get(EventDay, obj_in.event_day_id)
    if not event_day:
        raise ValueError(f"EventDay with id '{obj_in.event_day_id}' not found")

    if obj_in.end_min is not None and obj_in.end_min <= obj_in.start_min:
        raise ValueError("end_min must be greater than start_min")

    db_obj = OperationalEvent(**obj_in.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj


async def get_by_id(db: AsyncSession, id: UUID) -> OperationalEvent | None:
    return await db.get(OperationalEvent, id)


async def list_by_event_day(
    db: AsyncSession, event_day_id: str,
) -> list[OperationalEvent]:
    result = await db.execute(
        select(OperationalEvent).where(OperationalEvent.event_day_id == event_day_id)
    )
    return list(result.scalars().all())


async def list_active_by_event_day(
    db: AsyncSession, event_day_id: str, current_min: int,
) -> list[OperationalEvent]:
    result = await db.execute(
        select(OperationalEvent).where(
            OperationalEvent.event_day_id == event_day_id,
            OperationalEvent.is_active == True,
            OperationalEvent.start_min <= current_min,
            or_(
                OperationalEvent.end_min.is_(None),
                OperationalEvent.end_min > current_min,
            ),
        )
    )
    return list(result.scalars().all())


async def update(
    db: AsyncSession, db_obj: OperationalEvent, obj_in: OperationalEventUpdate,
) -> OperationalEvent:
    update_data = obj_in.model_dump(exclude_unset=True)

    if "start_min" in update_data or "end_min" in update_data:
        new_start = update_data.get("start_min", db_obj.start_min)
        new_end = update_data.get("end_min", db_obj.end_min)
        if new_end is not None and new_end <= new_start:
            raise ValueError("end_min must be greater than start_min")

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    await db.flush()
    await db.refresh(db_obj)
    return db_obj


async def delete(db: AsyncSession, id: UUID) -> bool:
    db_obj = await db.get(OperationalEvent, id)
    if not db_obj:
        return False
    await db.delete(db_obj)
    await db.flush()
    return True
