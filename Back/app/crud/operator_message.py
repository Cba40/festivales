"""CRUD operations for OperatorMessage (RFC-ALERTS-MESSAGES-V1)."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.operator_message import OperatorMessage
from app.models.transport_line import TransportLine
from app.schemas.operator_message import OperatorMessageCreate, OperatorMessageUpdate


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _validate_relations(db: AsyncSession, event_id: str, line_id: str | None) -> None:
    event_exists = await db.scalar(select(Event.id).where(Event.id == event_id))
    if not event_exists:
        raise ValueError(f"Event with id '{event_id}' not found")
    if line_id is not None:
        line_exists = await db.scalar(
            select(TransportLine.id).where(
                TransportLine.id == line_id,
                TransportLine.event_id == event_id,
            )
        )
        if not line_exists:
            raise ValueError(
                f"TransportLine with id '{line_id}' not found for event '{event_id}'"
            )


async def create(db: AsyncSession, data: OperatorMessageCreate) -> OperatorMessage:
    await _validate_relations(db, data.event_id, data.line_id)
    db_obj = OperatorMessage(**data.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get(db: AsyncSession, message_id: UUID) -> OperatorMessage | None:
    return await db.get(OperatorMessage, message_id)


async def list_by_event(db: AsyncSession, event_id: str) -> list[OperatorMessage]:
    result = await db.execute(
        select(OperatorMessage)
        .where(OperatorMessage.event_id == event_id)
        .order_by(OperatorMessage.publish_at)
    )
    return list(result.scalars().all())


async def list_active(db: AsyncSession, event_id: str, now: datetime) -> list[OperatorMessage]:
    result = await db.execute(
        select(OperatorMessage).where(
            OperatorMessage.event_id == event_id,
            OperatorMessage.status == "published",
            OperatorMessage.publish_at <= now,
            (OperatorMessage.expires_at.is_(None)) | (OperatorMessage.expires_at > now),
        )
    )
    return list(result.scalars().all())


async def update(
    db: AsyncSession, message_id: UUID, data: OperatorMessageUpdate,
) -> OperatorMessage:
    db_obj = await db.get(OperatorMessage, message_id)
    if not db_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OperatorMessage not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    if "line_id" in update_data:
        await _validate_relations(db, db_obj.event_id, update_data["line_id"])

    new_publish = update_data.get("publish_at", db_obj.publish_at)
    new_expires = update_data.get("expires_at", db_obj.expires_at)
    if new_expires is not None and new_expires <= new_publish:
        raise ValueError("expires_at must be greater than publish_at")

    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db_obj.updated_at = _now()

    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def publish(db: AsyncSession, message_id: UUID) -> OperatorMessage:
    db_obj = await db.get(OperatorMessage, message_id)
    if not db_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OperatorMessage not found",
        )
    db_obj.status = "published"
    db_obj.updated_at = _now()

    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def cancel(db: AsyncSession, message_id: UUID) -> OperatorMessage:
    db_obj = await db.get(OperatorMessage, message_id)
    if not db_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OperatorMessage not found",
        )
    db_obj.status = "cancelled"
    db_obj.updated_at = _now()

    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete(db: AsyncSession, message_id: UUID) -> None:
    db_obj = await db.get(OperatorMessage, message_id)
    if not db_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OperatorMessage not found",
        )
    await db.delete(db_obj)
    await db.flush()
    await db.commit()