from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_token
from app.crud import (
    create_event_day,
    delete_event_day,
    get_event_day,
    list_by_event,
    update_event_day,
)
from app.db.session import get_async_db
from app.schemas.event_day import (
    EventDayCreate,
    EventDayResponse,
    EventDaySummary,
    EventDayUpdate,
)

router = APIRouter(prefix="/api/events/{event_id}/event-days", tags=["event-days"])


@router.get("", response_model=list[EventDaySummary])
async def list_event_days(
    event_id: str,
    active: Optional[bool] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    result = await list_by_event(db, event_id, skip=skip, limit=limit)
    if active is not None:
        result = [d for d in result if d.is_active == active]
    return result


@router.get("/today", response_model=Optional[EventDayResponse])
async def get_today_event_day(
    event_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    today = date.today()
    result = await list_by_event(db, event_id)
    for d in result:
        if d.date == today and d.is_active:
            return d
    return None


@router.get("/{day_id}", response_model=EventDayResponse)
async def get_event_day(
    event_id: str,
    day_id: str,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    day = await get_event_day(db, day_id)
    if not day or day.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event day not found")
    return day


@router.post("", response_model=EventDayResponse, status_code=status.HTTP_201_CREATED)
async def create_event_day(
    event_id: str,
    body: EventDayCreate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    try:
        return await create_event_day(db, body, event_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.put("/{day_id}", response_model=EventDayResponse)
async def update_event_day(
    event_id: str,
    day_id: str,
    body: EventDayUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    day = await get_event_day(db, day_id)
    if not day or day.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event day not found")
    try:
        return await update_event_day(db, day, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete("/{day_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event_day(
    event_id: str,
    day_id: str,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    day = await get_event_day(db, day_id)
    if not day or day.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event day not found")
    await delete_event_day(db, day_id)
