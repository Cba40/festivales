from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import verify_token
from app.crud.event_day_zone_factor import event_day_zone_factor as edzf_crud
from app.crud.state_override import state_override as state_override_crud
from app.db.session import get_db
from app.models.event import Event
from app.models.event_day import EventDay
from app.models.event_day_zone_factor import EventDayZoneFactor
from app.models.state_override import StateOverride
from app.schemas.event_day_zone_factor import (
    EventDayZoneFactorCreate,
    EventDayZoneFactorResponse,
    EventDayZoneFactorUpdate,
)
from app.schemas.state_override import (
    StateOverrideCreate,
    StateOverrideResponse,
)
from app.schemas.zone_prediction import ContextEngineResponse, CurrentStateResponse
from app.services import context_engine

router = APIRouter(prefix="/api/events/{event_id}/context-engine", tags=["context-engine"])


def _get_event_or_404(db: Session, event_id: str) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


def _get_event_day_or_404(db: Session, event_id: str, day_id: str) -> EventDay:
    day = db.query(EventDay).filter(
        EventDay.id == day_id,
        EventDay.event_id == event_id,
    ).first()
    if not day:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event day not found")
    return day


@router.get("/state", response_model=CurrentStateResponse)
def get_current_state(
    event_id: str,
    datetime_actual: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _get_event_or_404(db, event_id)
    state, override = context_engine.get_current_state(db, event_id, datetime_actual)
    return {"estado_actual": state, "override_activo": override}


@router.get("/predictions", response_model=ContextEngineResponse)
def get_predictions(
    event_id: str,
    datetime_actual: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _get_event_or_404(db, event_id)
    result = context_engine.compute_predictions(db, event_id, datetime_actual)
    return result


@router.post("/overrides", response_model=StateOverrideResponse, status_code=status.HTTP_201_CREATED)
def create_override(
    event_id: str,
    body: StateOverrideCreate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _get_event_or_404(db, event_id)
    _get_event_day_or_404(db, event_id, body.event_day_id)
    override = state_override_crud.create(db, body)
    return override


@router.delete("/overrides/{override_id}", response_model=StateOverrideResponse)
def cancel_override(
    event_id: str,
    override_id: str,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _get_event_or_404(db, event_id)
    override = db.query(StateOverride).filter(StateOverride.id == override_id).first()
    if not override:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")
    day = db.query(EventDay).filter(
        EventDay.id == override.event_day_id,
        EventDay.event_id == event_id,
    ).first()
    if not day:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found for this event")
    override.is_active = False
    db.commit()
    db.refresh(override)
    return override


@router.get("/event-day-zone-factors", response_model=list[EventDayZoneFactorResponse])
def list_event_day_zone_factors(
    event_id: str,
    event_day_id: str = Query(...),
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _get_event_or_404(db, event_id)
    _get_event_day_or_404(db, event_id, event_day_id)
    factors = db.query(EventDayZoneFactor).filter(
        EventDayZoneFactor.event_day_id == event_day_id,
    ).all()
    return factors


@router.post("/event-day-zone-factors", response_model=EventDayZoneFactorResponse, status_code=status.HTTP_201_CREATED)
def create_event_day_zone_factor(
    event_id: str,
    body: EventDayZoneFactorCreate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _get_event_or_404(db, event_id)
    _get_event_day_or_404(db, event_id, body.event_day_id)
    factor = edzf_crud.create(db, body)
    return factor


@router.put("/event-day-zone-factors/{factor_id}", response_model=EventDayZoneFactorResponse)
def update_event_day_zone_factor(
    event_id: str,
    factor_id: str,
    body: EventDayZoneFactorUpdate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _get_event_or_404(db, event_id)
    factor = db.query(EventDayZoneFactor).filter(EventDayZoneFactor.id == factor_id).first()
    if not factor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factor not found")
    day = db.query(EventDay).filter(
        EventDay.id == factor.event_day_id,
        EventDay.event_id == event_id,
    ).first()
    if not day:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factor not found for this event")
    updated = edzf_crud.update(db, factor, body)
    return updated


@router.delete("/event-day-zone-factors/{factor_id}", response_model=EventDayZoneFactorResponse)
def delete_event_day_zone_factor(
    event_id: str,
    factor_id: str,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _get_event_or_404(db, event_id)
    factor = db.query(EventDayZoneFactor).filter(EventDayZoneFactor.id == factor_id).first()
    if not factor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factor not found")
    day = db.query(EventDay).filter(
        EventDay.id == factor.event_day_id,
        EventDay.event_id == event_id,
    ).first()
    if not day:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factor not found for this event")
    edzf_crud.delete(db, factor_id)
    return factor
