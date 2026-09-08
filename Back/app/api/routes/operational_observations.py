"""Endpoints for OperationalObservation (RFC-006): ingesta y consulta inmutable."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.operational_observation import create_observation, find_all, get_observation
from app.db.session import get_async_db
from app.schemas.operational_observation import (
    OperationalObservationCreate,
    OperationalObservationResponse,
)

router = APIRouter(prefix="/operational-observations", tags=["Operational Observations"])


@router.post("/", response_model=OperationalObservationResponse, status_code=status.HTTP_201_CREATED)
async def create_observation_endpoint(
    observation_in: OperationalObservationCreate,
    db: AsyncSession = Depends(get_async_db),
):
    try:
        return await create_observation(db, observation_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.get("/", response_model=list[OperationalObservationResponse])
async def list_observations(
    event_day_id: Optional[str] = None,
    zone_id: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    db: AsyncSession = Depends(get_async_db),
):
    return await find_all(
        db,
        event_day_id=event_day_id,
        zone_id=zone_id,
        start_date=start,
        end_date=end,
    )


@router.get("/{observation_id}", response_model=OperationalObservationResponse)
async def get_observation_endpoint(
    observation_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    result = await get_observation(db, observation_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OperationalObservation not found",
        )
    return result