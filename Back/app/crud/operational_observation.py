from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from src.domain.entities.operational_observation import OperationalObservation
from app.schemas.operational_observation import OperationalObservationCreate, OperationalObservationResponse


async def create_observation(
    db: AsyncSession,
    observation_in: OperationalObservationCreate,
) -> OperationalObservationResponse:
    observation = OperationalObservation(
        id=UUID(),
        event_day_id=observation_in.event_day_id,
        zone_id=observation_in.zone_id,
        timestamp=datetime.now(),
        observed_density=observation_in.observed_density,
        observer_id=observation_in.observer_id,
        source=observation_in.source,
        metadata=observation_in.metadata or {},
    )
    db.add(observation)
    await db.flush()
    await db.refresh(observation)
    return OperationalObservationResponse(
        id=str(observation.id),
        event_day_id=observation.event_day_id,
        zone_id=observation.zone_id,
        timestamp=observation.timestamp,
        observed_density=observation.observed_density,
        observer_id=observation.observer_id,
        source=observation.source,
        metadata=observation.metadata,
        created_at=observation.created_at,
    )


async def find_by_zone_and_date_range(
    db: AsyncSession,
    zone_id: str,
    start: datetime,
    end: datetime,
) -> list[OperationalObservationResponse]:
    result = await db.execute(
        select(OperationalObservation)
        .where(OperationalObservation.zone_id == zone_id)
        .where(OperationalObservation.timestamp >= start)
        .where(OperationalObservation.timestamp <= end)
    )
    models = result.scalars().all()
    return [
        OperationalObservationResponse(
            id=str(m.id),
            event_day_id=m.event_day_id,
            zone_id=m.zone_id,
            timestamp=m.timestamp,
            observed_density=m.observed_density,
            observer_id=m.observer_id,
            source=m.source,
            metadata=m.metadata,
            created_at=m.created_at,
        )
        for m in models
    ]