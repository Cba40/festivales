from datetime import date, datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import verify_token
from app.crud import (
    create_event_day,
    create_event_day_phase,
    delete_event_day,
    delete_event_day_phase,
    get_event_day,
    get_event_day_phase,
    list_by_event,
    list_phases_by_event_day,
    update_event_day,
    update_event_day_phase,
)
from app.db.session import get_async_db
from app.models.event_day import EventDay
from app.schemas.event_day import (
    EventDayCreate,
    EventDayResponse,
    EventDaySummary,
    EventDayUpdate,
)
from app.schemas.event_day_phase import (
    EventDayPhaseCreate,
    EventDayPhaseResponse,
    EventDayPhaseUpdate,
)

router = APIRouter(prefix="/api/events/{event_id}/event-days", tags=["event-days"])


async def _load_with_phases(db: AsyncSession, day_id: str) -> EventDay | None:
    from sqlalchemy import select as sa_select
    result = await db.execute(
        sa_select(EventDay)
        .where(EventDay.id == day_id)
        .options(selectinload(EventDay.phases))
    )
    return result.scalar_one_or_none()


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
            return await _load_with_phases(db, d.id)
    return None


@router.get("/{day_id}", response_model=EventDayResponse)
async def get_event_day(
    event_id: str,
    day_id: str,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    day = await _load_with_phases(db, day_id)
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


# ── Nested EventDayPhase routes ─────────────────────────────────────


@router.get("/{day_id}/phases", response_model=list[EventDayPhaseResponse])
async def list_phases(
    event_id: str,
    day_id: str,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    day = await get_event_day(db, day_id)
    if not day or day.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event day not found")
    return await list_phases_by_event_day(db, day_id)


@router.post("/{day_id}/phases", response_model=EventDayPhaseResponse, status_code=status.HTTP_201_CREATED)
async def create_phase(
    event_id: str,
    day_id: str,
    body: EventDayPhaseCreate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    day = await get_event_day(db, day_id)
    if not day or day.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event day not found")
    try:
        return await create_event_day_phase(db, day_id, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/{day_id}/phases/{phase_id}", response_model=EventDayPhaseResponse)
async def get_phase(
    event_id: str,
    day_id: str,
    phase_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    day = await get_event_day(db, day_id)
    if not day or day.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event day not found")
    phase = await get_event_day_phase(db, phase_id)
    if not phase or phase.event_day_id != day_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found")
    return phase


@router.put("/{day_id}/phases/{phase_id}", response_model=EventDayPhaseResponse)
async def update_phase(
    event_id: str,
    day_id: str,
    phase_id: UUID,
    body: EventDayPhaseUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    day = await get_event_day(db, day_id)
    if not day or day.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event day not found")
    phase = await get_event_day_phase(db, phase_id)
    if not phase or phase.event_day_id != day_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found")
    try:
        return await update_event_day_phase(db, phase, body)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete("/{day_id}/phases/{phase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_phase(
    event_id: str,
    day_id: str,
    phase_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    day = await get_event_day(db, day_id)
    if not day or day.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event day not found")
    phase = await get_event_day_phase(db, phase_id)
    if not phase or phase.event_day_id != day_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Phase not found")
    await delete_event_day_phase(db, phase_id)
