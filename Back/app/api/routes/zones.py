# backend/app/api/routes/zones.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.event import Event
from app.models.zone import Zone
from app.schemas.zone import (
    ZoneResponse,
    ZoneCreateRequest,
    ZoneUpdateRequest,
    ZoneConfigUpdateRequest,
)
from app.api.deps import verify_token

router = APIRouter(prefix="/api/events/{event_id}/zones", tags=["zones"])


@router.get("", response_model=list[ZoneResponse])
def list_zones(event_id: str, db: Session = Depends(get_db), _=Depends(verify_token)):
    zones = db.query(Zone).filter(Zone.event_id == event_id).all()
    return zones


@router.post("", response_model=ZoneResponse, status_code=status.HTTP_201_CREATED)
def create_zone(
    event_id: str,
    body: ZoneCreateRequest,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    zone = Zone(
        event_id=event_id,
        name=body.name,
        type=body.type,
        capacity=body.capacity,
        available_capacity=body.capacity,
        saturation="bajo",
        status="activa",
        latitude=body.latitude,
        longitude=body.longitude,
    )
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


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


@router.put("/{zone_id}/config", response_model=ZoneResponse)
def update_zone_config(
    event_id: str,
    zone_id: str,
    body: ZoneConfigUpdateRequest,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    zone = db.query(Zone).filter(Zone.id == zone_id, Zone.event_id == event_id).first()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    update_data = body.model_dump(exclude_unset=True)
    if "latitude" in update_data:
        update_data["latitude"] = body.latitude
    if "longitude" in update_data:
        update_data["longitude"] = body.longitude
    if "capacity" in update_data:
        update_data["available_capacity"] = body.capacity

    for field, value in update_data.items():
        setattr(zone, field, value)

    db.commit()
    db.refresh(zone)
    return zone


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_zone(
    event_id: str,
    zone_id: str,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    zone = db.query(Zone).filter(Zone.id == zone_id, Zone.event_id == event_id).first()
    if not zone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")

    db.delete(zone)
    db.commit()
