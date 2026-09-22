"""CRUD operations for TransportAlert (RFC-ALERTS-MESSAGES-V1)."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.transport_alert import TransportAlert
from app.models.transport_line import TransportLine
from app.schemas.transport_alert import TransportAlertCreate, TransportAlertUpdate


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


async def create(db: AsyncSession, data: TransportAlertCreate) -> TransportAlert:
    await _validate_relations(db, data.event_id, data.line_id)
    db_obj = TransportAlert(**data.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get(db: AsyncSession, alert_id: UUID) -> TransportAlert | None:
    return await db.get(TransportAlert, alert_id)


async def list_by_event(db: AsyncSession, event_id: str) -> list[TransportAlert]:
    result = await db.execute(
        select(TransportAlert)
        .where(TransportAlert.event_id == event_id)
        .order_by(TransportAlert.valid_from)
    )
    return list(result.scalars().all())


async def list_active(db: AsyncSession, event_id: str, now: datetime) -> list[TransportAlert]:
    result = await db.execute(
        select(TransportAlert).where(
            TransportAlert.event_id == event_id,
            TransportAlert.is_active.is_(True),
            TransportAlert.valid_from <= now,
            TransportAlert.valid_until > now,
        )
    )
    return list(result.scalars().all())


async def update(
    db: AsyncSession, alert_id: UUID, data: TransportAlertUpdate,
) -> TransportAlert:
    db_obj = await db.get(TransportAlert, alert_id)
    if not db_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TransportAlert not found",
        )

    update_data = data.model_dump(exclude_unset=True)

    if "line_id" in update_data:
        await _validate_relations(db, db_obj.event_id, update_data["line_id"])

    new_start = update_data.get("valid_from", db_obj.valid_from)
    new_end = update_data.get("valid_until", db_obj.valid_until)
    if new_end <= new_start:
        raise ValueError("valid_until must be greater than valid_from")

    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db_obj.updated_at = _now()

    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def deactivate(db: AsyncSession, alert_id: UUID) -> TransportAlert:
    db_obj = await db.get(TransportAlert, alert_id)
    if not db_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TransportAlert not found",
        )
    db_obj.is_active = False
    db_obj.updated_at = _now()

    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete(db: AsyncSession, alert_id: UUID) -> None:
    db_obj = await db.get(TransportAlert, alert_id)
    if not db_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TransportAlert not found",
        )
    await db.delete(db_obj)
    await db.flush()
    await db.commit()