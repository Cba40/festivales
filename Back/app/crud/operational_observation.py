"""CRUD operations for OperationalObservation (RFC-006)."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_day import EventDay
from app.models.zone import Zone
from app.schemas.operational_observation import (
    OperationalObservationCreate,
    OperationalObservationResponse,
)
from src.infrastructure.persistence.models import OperationalObservationModel

LOCAL_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def _to_current_min(event_date: date, timestamp: datetime) -> int:
    local_ts = timestamp.astimezone(LOCAL_TZ)
    days_diff = (local_ts.date() - event_date).days
    return days_diff * 1440 + local_ts.hour * 60 + local_ts.minute


def _is_within_event_day(event_day: EventDay, timestamp: datetime) -> bool:
    current_min = _to_current_min(event_day.date, timestamp)
    return event_day.operational_start_min <= current_min < event_day.operational_end_min


def _to_response(model: OperationalObservationModel) -> OperationalObservationResponse:
    return OperationalObservationResponse(
        id=str(model.id),
        event_day_id=model.event_day_id,
        zone_id=model.zone_id,
        timestamp=model.timestamp,
        observed_density=model.observed_density,
        observer_id=model.observer_id,
        source=model.source,
        metadata=model.metadata_,
        created_at=model.created_at,
    )


async def create_observation(
    db: AsyncSession,
    observation_in: OperationalObservationCreate,
) -> OperationalObservationResponse:
    event_day = await db.get(EventDay, observation_in.event_day_id)
    if not event_day:
        raise ValueError(f"EventDay with id '{observation_in.event_day_id}' not found")

    zone = await db.get(Zone, observation_in.zone_id)
    if not zone:
        raise ValueError(f"Zone with id '{observation_in.zone_id}' not found")

    timestamp = observation_in.timestamp
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")

    if not _is_within_event_day(event_day, timestamp):
        raise ValueError(
            f"timestamp {timestamp.isoformat()} is outside the operational range "
            f"of EventDay '{observation_in.event_day_id}'"
        )

    db_obj = OperationalObservationModel(
        event_day_id=observation_in.event_day_id,
        zone_id=observation_in.zone_id,
        timestamp=timestamp,
        observed_density=observation_in.observed_density,
        observer_id=observation_in.observer_id,
        source=observation_in.source,
        metadata_=observation_in.metadata,
    )
    db.add(db_obj)
    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return _to_response(db_obj)


async def get_observation(
    db: AsyncSession,
    observation_id: UUID,
) -> OperationalObservationResponse | None:
    model = await db.get(OperationalObservationModel, observation_id)
    if model is None:
        return None
    return _to_response(model)


async def find_all(
    db: AsyncSession,
    event_day_id: str | None = None,
    zone_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[OperationalObservationResponse]:
    stmt = select(OperationalObservationModel)
    if event_day_id is not None:
        stmt = stmt.where(OperationalObservationModel.event_day_id == event_day_id)
    if zone_id is not None:
        stmt = stmt.where(OperationalObservationModel.zone_id == zone_id)
    if start_date is not None:
        stmt = stmt.where(OperationalObservationModel.timestamp >= start_date)
    if end_date is not None:
        stmt = stmt.where(OperationalObservationModel.timestamp <= end_date)
    stmt = stmt.order_by(OperationalObservationModel.timestamp)

    result = await db.execute(stmt)
    models = result.scalars().all()
    return [_to_response(m) for m in models]