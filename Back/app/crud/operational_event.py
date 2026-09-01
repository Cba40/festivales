"""CRUD operations for OperationalEvent (RFC-OPERATIONAL-EVENTS-V1)."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_day import EventDay
from app.models.operational_event import OperationalEvent
from app.models.zone import Zone
from app.schemas.operational_event import (
    OperationalEventCreate,
    OperationalEventUpdate,
)
from app.schemas.operational_event import validate_effect


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(db_obj: OperationalEvent, now: datetime) -> bool:
    return now >= db_obj.end_timestamp


async def create(db: AsyncSession, data: OperationalEventCreate) -> OperationalEvent:
    event_day_exists = await db.scalar(
        select(EventDay.id).where(EventDay.id == data.event_day_id)
    )
    if not event_day_exists:
        raise ValueError(f"EventDay with id '{data.event_day_id}' not found")

    zone_exists = await db.scalar(select(Zone.id).where(Zone.id == data.zone_id))
    if not zone_exists:
        raise ValueError(f"Zone with id '{data.zone_id}' not found")

    db_obj = OperationalEvent(**data.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get(db: AsyncSession, event_id: UUID) -> OperationalEvent | None:
    return await db.get(OperationalEvent, event_id)


async def list_by_event_day(
    db: AsyncSession, event_day_id: str,
) -> list[OperationalEvent]:
    result = await db.execute(
        select(OperationalEvent)
        .where(OperationalEvent.event_day_id == event_day_id)
        .order_by(OperationalEvent.start_timestamp)
    )
    return list(result.scalars().all())


async def update(
    db: AsyncSession, event_id: UUID, data: OperationalEventUpdate,
) -> OperationalEvent:
    db_obj = await db.get(OperationalEvent, event_id)
    if not db_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OperationalEvent not found",
        )
    if _is_expired(db_obj, _now()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify expired event",
        )

    update_data = data.model_dump(exclude_unset=True)

    new_start = update_data.get("start_timestamp", db_obj.start_timestamp)
    new_end = update_data.get("end_timestamp", db_obj.end_timestamp)
    if new_end <= new_start:
        raise ValueError("end_timestamp must be greater than start_timestamp")

    new_effect_type = update_data.get("effect_type", db_obj.effect_type)
    new_effect_value = update_data.get("effect_value", db_obj.effect_value)
    validate_effect(new_effect_type, new_effect_value)

    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db_obj.updated_at = _now()

    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def deactivate(db: AsyncSession, event_id: UUID) -> OperationalEvent:
    db_obj = await db.get(OperationalEvent, event_id)
    if not db_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OperationalEvent not found",
        )
    if _is_expired(db_obj, _now()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate expired event",
        )

    db_obj.is_active = False
    db_obj.updated_at = _now()

    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete(db: AsyncSession, event_id: UUID) -> None:
    db_obj = await db.get(OperationalEvent, event_id)
    if not db_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OperationalEvent not found",
        )
    if _is_expired(db_obj, _now()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete event that has been used by the prediction engine",
        )

    await db.delete(db_obj)
    await db.flush()
    await db.commit()