"""Endpoints for OperationalEvent."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_token
from app.crud import (
    create_operational_event,
    delete_operational_event,
    get_operational_event,
    list_events_by_event_day,
    update_operational_event,
)
from app.db.session import get_async_db
from app.schemas.operational_event import (
    OperationalEventCreate,
    OperationalEventResponse,
    OperationalEventUpdate,
)

router = APIRouter(prefix="/operational-events", tags=["Operational Events"])


@router.post("/", response_model=OperationalEventResponse, status_code=status.HTTP_201_CREATED)
async def create(
    obj_in: OperationalEventCreate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    try:
        return await create_operational_event(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/{event_id}", response_model=OperationalEventResponse)
async def get_by_id(
    event_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    db_obj = await get_operational_event(db, event_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OperationalEvent not found")
    return db_obj


@router.get("/by-event-day/{event_day_id}", response_model=list[OperationalEventResponse])
async def list_by_event_day(
    event_day_id: str,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await list_events_by_event_day(db, event_day_id)


@router.put("/{event_id}", response_model=OperationalEventResponse)
async def update(
    event_id: UUID,
    obj_in: OperationalEventUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    db_obj = await get_operational_event(db, event_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OperationalEvent not found")
    try:
        return await update_operational_event(db, db_obj, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    event_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    deleted = await delete_operational_event(db, event_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OperationalEvent not found")
