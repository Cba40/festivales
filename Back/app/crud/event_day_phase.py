"""CRUD operations for EventDayPhase."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_day_phase import EventDayPhase
from app.models.operational_phase import OperationalPhase
from app.schemas.event_day_phase import EventDayPhaseCreate, EventDayPhaseUpdate


async def create(
    db: AsyncSession, event_day_id: str, obj_in: EventDayPhaseCreate,
) -> EventDayPhase:
    op_phase = await db.get(OperationalPhase, obj_in.operational_phase_id)
    if not op_phase:
        raise ValueError(
            f"OperationalPhase with id '{obj_in.operational_phase_id}' not found"
        )

    if obj_in.end_min <= obj_in.start_min:
        raise ValueError("end_min must be greater than start_min")

    db_obj = EventDayPhase(
        event_day_id=event_day_id,
        operational_phase_id=obj_in.operational_phase_id,
        start_min=obj_in.start_min,
        end_min=obj_in.end_min,
    )
    db.add(db_obj)
    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get_by_id(db: AsyncSession, id: UUID) -> EventDayPhase | None:
    return await db.get(EventDayPhase, id)


async def list_by_event_day(
    db: AsyncSession, event_day_id: str,
) -> list[EventDayPhase]:
    result = await db.execute(
        select(EventDayPhase)
        .where(EventDayPhase.event_day_id == event_day_id)
        .order_by(EventDayPhase.start_min)
    )
    return list(result.scalars().all())


async def update(
    db: AsyncSession, db_obj: EventDayPhase, obj_in: EventDayPhaseUpdate,
) -> EventDayPhase:
    update_data = obj_in.model_dump(exclude_unset=True)

    if "operational_phase_id" in update_data:
        op_phase = await db.get(OperationalPhase, update_data["operational_phase_id"])
        if not op_phase:
            raise ValueError(
                f"OperationalPhase with id '{update_data['operational_phase_id']}' not found"
            )

    if "start_min" in update_data or "end_min" in update_data:
        new_start = update_data.get("start_min", db_obj.start_min)
        new_end = update_data.get("end_min", db_obj.end_min)
        if new_end <= new_start:
            raise ValueError("end_min must be greater than start_min")

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete(db: AsyncSession, id: UUID) -> bool:
    db_obj = await db.get(EventDayPhase, id)
    if not db_obj:
        return False
    await db.delete(db_obj)
    await db.flush()
    await db.commit()
    return True
