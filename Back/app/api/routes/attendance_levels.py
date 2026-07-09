from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import verify_token
from app.crud.attendance_level import attendance_level as crud
from app.db.session import get_db
from app.models.event import Event
from app.schemas.attendance_level import (
    AttendanceLevelCreate,
    AttendanceLevelResponse,
    AttendanceLevelUpdate,
)

router = APIRouter(prefix="/api/events/{event_id}/attendance-levels", tags=["attendance-levels"])


def _get_event_or_404(db: Session, event_id: str) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.get("", response_model=list[AttendanceLevelResponse])
def list_attendance_levels(
    event_id: str,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _get_event_or_404(db, event_id)
    return crud.get_by_event(db, event_id)


@router.post("", response_model=AttendanceLevelResponse, status_code=status.HTTP_201_CREATED)
def create_attendance_level(
    event_id: str,
    body: AttendanceLevelCreate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _get_event_or_404(db, event_id)
    return crud.create(db, body, event_id)


@router.put("/{level_id}", response_model=AttendanceLevelResponse)
def update_attendance_level(
    event_id: str,
    level_id: str,
    body: AttendanceLevelUpdate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _get_event_or_404(db, event_id)
    db_obj = crud.get(db, level_id)
    if not db_obj or db_obj.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance level not found")
    return crud.update(db, db_obj, body)


@router.delete("/{level_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attendance_level(
    event_id: str,
    level_id: str,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _get_event_or_404(db, event_id)
    db_obj = crud.get(db, level_id)
    if not db_obj or db_obj.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance level not found")
    crud.delete(db, level_id)
