"""CRUD operations for OperationalObservation."""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_day import EventDay
from app.models.operational_observation import OperationalObservation
from app.models.zone import Zone
from app.schemas.operational_observation import OperationalObservationCreate


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def create(db: AsyncSession, data: OperationalObservationCreate) -> OperationalObservation:
    event_day_exists = await db.scalar(
        select(EventDay.id).where(EventDay.id == str(data.event_day_id))
    )
    if not event_day_exists:
        raise ValueError(f"EventDay with id '{data.event_day_id}' not found")

    zone_exists = await db.scalar(select(Zone.id).where(Zone.id == str(data.zone_id)))
    if not zone_exists:
        raise ValueError(f"Zone with id '{data.zone_id}' not found")

    payload = data.model_dump()
    # Convert UUID to string for DB storage
    payload["event_day_id"] = str(payload["event_day_id"])
    payload["zone_id"] = str(payload["zone_id"])
    if payload.get("observer_id") is not None:
        payload["observer_id"] = str(payload["observer_id"])

    db_obj = OperationalObservation(**payload)
    db.add(db_obj)
    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get(db: AsyncSession, observation_id: UUID) -> OperationalObservation | None:
    return await db.get(OperationalObservation, observation_id)


async def list_observations(
    db: AsyncSession,
    event_day_id: UUID | None = None,
    zone_id: UUID | None = None,
) -> list[OperationalObservation]:
    stmt = select(OperationalObservation).order_by(OperationalObservation.timestamp)

    if event_day_id is not None:
        stmt = stmt.where(OperationalObservation.event_day_id == str(event_day_id))
    if zone_id is not None:
        stmt = stmt.where(OperationalObservation.zone_id == str(zone_id))

    result = await db.execute(stmt)
    return list(result.scalars().all())