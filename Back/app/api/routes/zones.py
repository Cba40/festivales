# backend/app/api/routes/zones.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.zone import Zone
from app.schemas.zone import ZoneResponse, ZoneUpdateRequest
from app.api.deps import verify_token

router = APIRouter(prefix="/api/events/{event_id}/zones", tags=["zones"])


@router.get("", response_model=list[ZoneResponse])
def list_zones(event_id: str, db: Session = Depends(get_db), _=Depends(verify_token)):
    zones = db.query(Zone).filter(Zone.event_id == event_id).all()
    return zones


@router.patch("/{zone_id}", response_model=ZoneResponse)
def update_zone(
    event_id: str,
    zone_id: str,
    body: ZoneUpdateRequest,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    zone = db.query(Zone).filter(Zone.id == zone_id, Zone.event_id == event_id).first()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(zone, field, value)

    db.commit()
    db.refresh(zone)
    return zone
