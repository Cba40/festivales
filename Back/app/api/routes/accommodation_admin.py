"""Gestión administrativa de Hospedaje V1 (Dashboard > Infraestructura > Hospedaje).

CRUD plano y directo sobre la entidad ``accommodations``: crear, listar,
actualizar y desactivar alojamientos. Sin lógica de reservas, habitaciones
ni calendarios (es un CRUD informativo).

Patrón idéntico a transport_admin.py: prefijo /api/events/{event_id},
lecturas públicas y escrituras con verify_token.

El DELETE es un *soft delete*: establece ``active = False`` para preservar la
integridad histórica (los alojamientos desactivados dejan de exponerse en el
endpoint público pero se mantienen en la base).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import verify_token
from app.db.session import get_db
from app.models.accommodation import Accommodation
from app.models.event import Event
from app.schemas.accommodation_admin import (
    AccommodationCreate,
    AccommodationResponse,
    AccommodationUpdate,
)

router = APIRouter(prefix="/api/events/{event_id}", tags=["Accommodation Admin"])


def _evento_existe(db: Session, event_id: str) -> bool:
    return db.query(Event.id).filter(Event.id == event_id).first() is not None


def _require_event(db: Session, event_id: str) -> None:
    if not _evento_existe(db, event_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")


def _get_accommodation_or_404(db: Session, event_id: str, accommodation_id: str) -> Accommodation:
    acc = (
        db.query(Accommodation)
        .filter(Accommodation.id == accommodation_id, Accommodation.event_id == event_id)
        .first()
    )
    if not acc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Accommodation not found",
        )
    return acc


@router.get("/accommodations", response_model=list[AccommodationResponse])
def list_accommodations(
    event_id: str,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    _require_event(db, event_id)
    query = db.query(Accommodation).filter(Accommodation.event_id == event_id)
    if not include_inactive:
        query = query.filter(Accommodation.active == True)  # noqa: E712
    return query.order_by(Accommodation.name).all()


@router.post("/accommodations", response_model=AccommodationResponse, status_code=status.HTTP_201_CREATED)
def create_accommodation(
    event_id: str,
    body: AccommodationCreate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _require_event(db, event_id)

    name = body.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name must not be empty",
        )

    exists = (
        db.query(Accommodation)
        .filter(Accommodation.event_id == event_id, Accommodation.name == name)
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Accommodation already exists for this event",
        )

    acc = Accommodation(
        event_id=event_id,
        name=name,
        type=body.type,
        address=_clean(body.address),
        reference=_clean(body.reference),
        latitude=body.latitude,
        longitude=body.longitude,
        phone=_clean(body.phone),
        website=_clean(body.website),
        official_info_url=_clean(body.official_info_url),
        active=body.active,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    return acc


@router.put("/accommodations/{accommodation_id}", response_model=AccommodationResponse)
def update_accommodation(
    event_id: str,
    accommodation_id: str,
    body: AccommodationUpdate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    acc = _get_accommodation_or_404(db, event_id, accommodation_id)

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Name must not be empty",
            )
        if name != acc.name:
            conflict = (
                db.query(Accommodation)
                .filter(
                    Accommodation.event_id == event_id,
                    Accommodation.name == name,
                    Accommodation.id != accommodation_id,
                )
                .first()
            )
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Accommodation already exists for this event",
                )
            acc.name = name

    if body.type is not None:
        acc.type = body.type
    if body.address is not None:
        acc.address = _clean(body.address)
    if body.reference is not None:
        acc.reference = _clean(body.reference)
    if body.latitude is not None:
        acc.latitude = body.latitude
    if body.longitude is not None:
        acc.longitude = body.longitude
    if body.phone is not None:
        acc.phone = _clean(body.phone)
    if body.website is not None:
        acc.website = _clean(body.website)
    if body.official_info_url is not None:
        acc.official_info_url = _clean(body.official_info_url)
    if body.active is not None:
        acc.active = body.active

    db.commit()
    db.refresh(acc)
    return acc


@router.delete("/accommodations/{accommodation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_accommodation(
    event_id: str,
    accommodation_id: str,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    acc = _get_accommodation_or_404(db, event_id, accommodation_id)
    # Soft delete: ocultamos del endpoint público sin borrar históricos.
    acc.active = False
    db.commit()


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
