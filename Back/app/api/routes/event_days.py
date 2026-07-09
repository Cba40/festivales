from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import verify_token
from app.db.session import get_db
from app.models.event import Event
from app.models.event_day import EventDay
from app.schemas.event_day import (
    EventDayCreate,
    EventDayResponse,
    EventDaySummary,
    EventDayUpdate,
)

router = APIRouter(prefix="/api/events/{event_id}/event-days", tags=["event-days"])


@router.get("", response_model=list[EventDaySummary])
def list_event_days(
    event_id: str,
    active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    query = db.query(EventDay).filter(EventDay.event_id == event_id)
    if active is not None:
        query = query.filter(EventDay.is_active == active)
    days = query.order_by(EventDay.date.desc()).all()
    return days


@router.get("/today", response_model=Optional[EventDayResponse])
def get_today_event_day(
    event_id: str,
    db: Session = Depends(get_db),
):
    today = date.today()
    day = db.query(EventDay).filter(
        EventDay.event_id == event_id,
        EventDay.date == today,
        EventDay.is_active == True,
    ).first()
    return day


@router.get("/{day_id}", response_model=EventDayResponse)
def get_event_day(
    event_id: str,
    day_id: str,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    day = db.query(EventDay).filter(
        EventDay.id == day_id,
        EventDay.event_id == event_id,
    ).first()
    if not day:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event day not found")
    return day


@router.post("", response_model=EventDayResponse, status_code=status.HTTP_201_CREATED)
def create_event_day(
    event_id: str,
    body: EventDayCreate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    day = EventDay(
        event_id=event_id,
        date=body.date,
        day_of_week=body.day_of_week,
        entry_start_min=body.entry_start_min,
        activity_peak_start_min=body.activity_peak_start_min,
        activity_peak_end_min=body.activity_peak_end_min,
        exit_start_min=body.exit_start_min,
        event_end_min=body.event_end_min,
        weather=body.weather,
        headliner_artist=body.headliner_artist,
        estimated_attendance=body.estimated_attendance,
        notes=body.notes,
        is_active=body.is_active,
    )
    db.add(day)
    db.commit()
    db.refresh(day)
    return day


@router.put("/{day_id}", response_model=EventDayResponse)
def update_event_day(
    event_id: str,
    day_id: str,
    body: EventDayUpdate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    day = db.query(EventDay).filter(
        EventDay.id == day_id,
        EventDay.event_id == event_id,
    ).first()
    if not day:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event day not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(day, field, value)

    db.commit()
    db.refresh(day)
    return day


@router.delete("/{day_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event_day(
    event_id: str,
    day_id: str,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    day = db.query(EventDay).filter(
        EventDay.id == day_id,
        EventDay.event_id == event_id,
    ).first()
    if not day:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event day not found")

    db.delete(day)
    db.commit()
