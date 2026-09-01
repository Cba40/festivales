"""Endpoints for OperationalEvent (RFC-OPERATIONAL-EVENTS-V1, Fase 2)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_token
from app.crud.operational_event import (
    create,
    deactivate,
    delete,
    get,
    list_by_event_day,
    update,
)
from app.db.session import get_async_db
from app.schemas.operational_event import (
    OperationalEventCreate,
    OperationalEventResponse,
    OperationalEventUpdate,
)

router = APIRouter(prefix="/operational-events", tags=["Operational Events"])


@router.get("/by-event-day/{event_day_id}", response_model=list[OperationalEventResponse])
async def list_by_event_day_endpoint(
    event_day_id: str,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await list_by_event_day(db, event_day_id)


@router.get("/{event_id}", response_model=OperationalEventResponse)
async def get_endpoint(
    event_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    db_obj = await get(db, event_id)
    if not db_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OperationalEvent not found",
        )
    return db_obj


@router.post("/", response_model=OperationalEventResponse, status_code=status.HTTP_201_CREATED)
async def create_endpoint(
    obj_in: OperationalEventCreate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    try:
        return await create(db, obj_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.put("/{event_id}", response_model=OperationalEventResponse)
async def update_endpoint(
    event_id: UUID,
    obj_in: OperationalEventUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    try:
        return await update(db, event_id, obj_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.patch("/{event_id}/deactivate", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_endpoint(
    event_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    await deactivate(db, event_id)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint(
    event_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    await delete(db, event_id)