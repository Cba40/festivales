# backend/app/api/routes/exit_admin.py
# Gestión de destinos de salida y su relación N:N con zonas tipo 'salida'
# (Dashboard > Infraestructura > Salidas y Destinos).
# Patrón idéntico a zones.py: prefijo /api/events/{event_id}, lecturas
# públicas y escrituras con verify_token.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import verify_token
from app.db.session import get_db
from app.models.event import Event
from app.models.exit_destination import ExitDestination
from app.models.exit_zone_destination import exit_zone_destinations_table
from app.models.zone import Zone
from app.schemas.exit_admin import (
    ExitDestinationCreate,
    ExitDestinationResponse,
    ExitDestinationUpdate,
    ZoneExitDestinationsResponse,
    ZoneExitDestinationsUpdate,
)

router = APIRouter(prefix="/api/events/{event_id}", tags=["Exit Admin"])


def _evento_existe(db: Session, event_id: str) -> bool:
    # Chequeo por columna: evita cargar la entidad completa (events tiene
    # una columna geometry con dependencia PostGIS innecesaria aquí).
    return db.query(Event.id).filter(Event.id == event_id).first() is not None


def _get_destination_or_404(db: Session, event_id: str, destination_id: str) -> ExitDestination:
    destination = (
        db.query(ExitDestination)
        .filter(ExitDestination.id == destination_id, ExitDestination.event_id == event_id)
        .first()
    )
    if not destination:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Exit destination not found"
        )
    return destination


@router.get("/exit-destinations", response_model=list[ExitDestinationResponse])
def list_exit_destinations(event_id: str, db: Session = Depends(get_db)):
    if not _evento_existe(db, event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return (
        db.query(ExitDestination)
        .filter(ExitDestination.event_id == event_id)
        .order_by(ExitDestination.name)
        .all()
    )


@router.post("/exit-destinations", response_model=ExitDestinationResponse, status_code=status.HTTP_201_CREATED)
def create_exit_destination(
    event_id: str,
    body: ExitDestinationCreate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    if not _evento_existe(db, event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    name = body.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name must not be empty"
        )

    exists = (
        db.query(ExitDestination)
        .filter(ExitDestination.event_id == event_id, ExitDestination.name == name)
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Exit destination already exists for this event",
        )

    destination = ExitDestination(event_id=event_id, name=name, active=body.active)
    db.add(destination)
    db.commit()
    db.refresh(destination)
    return destination


@router.put("/exit-destinations/{destination_id}", response_model=ExitDestinationResponse)
def update_exit_destination(
    event_id: str,
    destination_id: str,
    body: ExitDestinationUpdate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    destination = _get_destination_or_404(db, event_id, destination_id)

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Name must not be empty"
            )
        if name != destination.name:
            conflict = (
                db.query(ExitDestination)
                .filter(
                    ExitDestination.event_id == event_id,
                    ExitDestination.name == name,
                    ExitDestination.id != destination_id,
                )
                .first()
            )
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Exit destination already exists for this event",
                )
            destination.name = name

    if body.active is not None:
        destination.active = body.active

    db.commit()
    db.refresh(destination)
    return destination


@router.delete("/exit-destinations/{destination_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exit_destination(
    event_id: str,
    destination_id: str,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    destination = _get_destination_or_404(db, event_id, destination_id)
    db.delete(destination)
    db.commit()


def _get_zone_id_or_404(db: Session, event_id: str, zone_id: str) -> str:
    row = db.query(Zone.id).filter(Zone.id == zone_id, Zone.event_id == event_id).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zone not found")
    return row.id


def _assigned_destination_ids(db: Session, zone_id: str) -> list[str]:
    rows = (
        db.query(exit_zone_destinations_table.c.destination_id)
        .filter(exit_zone_destinations_table.c.exit_zone_id == zone_id)
        .all()
    )
    return [row.destination_id for row in rows]


@router.get("/zones/{zone_id}/exit-destinations", response_model=ZoneExitDestinationsResponse)
def get_zone_exit_destinations(event_id: str, zone_id: str, db: Session = Depends(get_db)):
    zone_id = _get_zone_id_or_404(db, event_id, zone_id)
    return ZoneExitDestinationsResponse(
        zone_id=zone_id, destination_ids=_assigned_destination_ids(db, zone_id)
    )


@router.put("/zones/{zone_id}/exit-destinations", response_model=ZoneExitDestinationsResponse)
def update_zone_exit_destinations(
    event_id: str,
    zone_id: str,
    body: ZoneExitDestinationsUpdate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    zone_id = _get_zone_id_or_404(db, event_id, zone_id)

    requested_ids = list(dict.fromkeys(body.destination_ids))
    if requested_ids:
        found = (
            db.query(ExitDestination.id)
            .filter(
                ExitDestination.event_id == event_id,
                ExitDestination.id.in_(requested_ids),
            )
            .all()
        )
        found_ids = {row.id for row in found}
        missing = [d for d in requested_ids if d not in found_ids]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Unknown exit destinations for this event: {missing}",
            )

    db.execute(
        exit_zone_destinations_table.delete().where(
            exit_zone_destinations_table.c.exit_zone_id == zone_id
        )
    )
    if requested_ids:
        db.execute(
            exit_zone_destinations_table.insert(),
            [{"exit_zone_id": zone_id, "destination_id": d} for d in requested_ids],
        )
    db.commit()

    return ZoneExitDestinationsResponse(zone_id=zone_id, destination_ids=requested_ids)
