# backend/app/api/routes/incidents.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.incident import Incident
from app.models.zone import Zone
from app.schemas.incident import IncidentCreate, IncidentResponse
from app.api.deps import verify_token

router = APIRouter(prefix="/api/events/{event_id}/incidents", tags=["incidents"])


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(
    event_id: str,
    body: IncidentCreate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    if body.zone_id:
        zone = db.query(Zone).filter(Zone.id == body.zone_id, Zone.event_id == event_id).first()
        if not zone:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    incident = Incident(
        event_id=event_id,
        type=body.type,
        severity=body.severity,
        description=body.description,
        zone_id=body.zone_id,
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return incident
