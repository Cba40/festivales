from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import verify_token
from app.db.session import get_db
from app.crud import event_state, zone_type
from app.schemas.event_state import EventStateResponse
from app.schemas.zone_type import ZoneTypeResponse

router = APIRouter(prefix="/api/context-engine", tags=["context-engine"])


@router.get("/event-states", response_model=list[EventStateResponse])
def get_event_states(
    event_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _: None = Depends(verify_token),
):
    """Return all EventStates. If event_id is provided, global states (event_id=null)
    are returned first, followed by event-specific states."""
    states = event_state.get_multi(db)
    if event_id:
        global_states = [s for s in states if s.event_id is None]
        event_states = [s for s in states if s.event_id == event_id]
        return global_states + event_states
    return states


@router.get("/zone-types", response_model=list[ZoneTypeResponse])
def get_zone_types(
    db: Session = Depends(get_db),
    _: None = Depends(verify_token),
):
    """Return all ZoneTypes."""
    return zone_type.get_multi(db)
