"""Gestión administrativa de Emergencia V1 (Dashboard > Infraestructura > Emergencias).

CRUD plano y directo sobre la entidad ``emergencies``: crear, listar, actualizar
y desactivar puntos de emergencia. Sin lógica de incidentes ni recursos
(es un CRUD informativo).

El módulo es transversal por CIUDAD (no por evento), por lo que el router usa el
prefijo ``/api/admin``. ``GET /api/admin/cities`` alimenta el selector de ciudad
del panel. Las escrituras usan ``verify_token``; las lecturas son públicas.

El DELETE es un *soft delete*: establece ``active = False`` para preservar la
integridad histórica (los desactivados dejan de exponerse en el endpoint público
pero se mantienen en la base).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import verify_token
from app.db.session import get_db
from app.models.city import City
from app.models.emergency import Emergency
from app.schemas.emergency_admin import (
    CityCreate,
    CityResponse,
    EmergencyCreate,
    EmergencyResponse,
    EmergencyUpdate,
)

router = APIRouter(prefix="/api/admin", tags=["Emergency Admin"])


def _city_exists(db: Session, city_id: str) -> bool:
    return db.query(City.id).filter(City.id == city_id).first() is not None


def _require_city(db: Session, city_id: str) -> None:
    if not _city_exists(db, city_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found")


def _get_emergency_or_404(db: Session, emergency_id: str) -> Emergency:
    em = db.query(Emergency).filter(Emergency.id == emergency_id).first()
    if not em:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Emergency not found",
        )
    return em


def _name_conflict(db: Session, city_id: str, name: str, exclude_id: str | None = None) -> bool:
    query = db.query(Emergency).filter(Emergency.city_id == city_id, Emergency.name == name)
    if exclude_id is not None:
        query = query.filter(Emergency.id != exclude_id)
    return query.first() is not None


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


@router.get("/cities", response_model=list[CityResponse])
def list_cities(
    db: Session = Depends(get_db),
):
    return db.query(City).order_by(City.name).all()


@router.post("/cities", response_model=CityResponse, status_code=status.HTTP_201_CREATED)
def create_city(
    body: CityCreate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name must not be empty",
        )

    province = _clean(body.province)
    country = (body.country or "Argentina").strip() or "Argentina"

    existing = db.query(City).filter(
        City.name == name,
        City.province == province,
        City.country == country,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="City already exists",
        )

    city = City(name=name, province=province, country=country)
    db.add(city)
    db.commit()
    db.refresh(city)
    return city


@router.get("/emergencies", response_model=list[EmergencyResponse])
def list_emergencies(
    city_id: str | None = None,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
):
    query = db.query(Emergency)
    if city_id is not None:
        query = query.filter(Emergency.city_id == city_id)
    if not include_inactive:
        query = query.filter(Emergency.active == True)  # noqa: E712
    return query.order_by(Emergency.name).all()


@router.post("/emergencies", response_model=EmergencyResponse, status_code=status.HTTP_201_CREATED)
def create_emergency(
    body: EmergencyCreate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    _require_city(db, body.city_id)

    name = body.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Name must not be empty",
        )

    if _name_conflict(db, body.city_id, name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Emergency already exists for this city",
        )

    em = Emergency(
        city_id=body.city_id,
        name=name,
        type=body.type,
        phone=_clean(body.phone),
        emergency_number=_clean(body.emergency_number),
        address=_clean(body.address),
        reference=_clean(body.reference),
        latitude=body.latitude,
        longitude=body.longitude,
        services=_clean(body.services),
        schedule=_clean(body.schedule),
        active=body.active,
    )
    db.add(em)
    db.commit()
    db.refresh(em)
    return em


@router.put("/emergencies/{emergency_id}", response_model=EmergencyResponse)
def update_emergency(
    emergency_id: str,
    body: EmergencyUpdate,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    em = _get_emergency_or_404(db, emergency_id)

    if body.city_id is not None:
        _require_city(db, body.city_id)
        em.city_id = body.city_id

    if body.name is not None:
        name = body.name.strip()
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Name must not be empty",
            )
        if _name_conflict(db, em.city_id, name, exclude_id=em.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Emergency already exists for this city",
            )
        em.name = name

    if body.type is not None:
        em.type = body.type
    if body.phone is not None:
        em.phone = _clean(body.phone)
    if body.emergency_number is not None:
        em.emergency_number = _clean(body.emergency_number)
    if body.address is not None:
        em.address = _clean(body.address)
    if body.reference is not None:
        em.reference = _clean(body.reference)
    if body.latitude is not None:
        em.latitude = body.latitude
    if body.longitude is not None:
        em.longitude = body.longitude
    if body.services is not None:
        em.services = _clean(body.services)
    if body.schedule is not None:
        em.schedule = _clean(body.schedule)
    if body.active is not None:
        em.active = body.active

    db.commit()
    db.refresh(em)
    return em


@router.delete("/emergencies/{emergency_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_emergency(
    emergency_id: str,
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    em = _get_emergency_or_404(db, emergency_id)
    # Soft delete: ocultamos del endpoint público sin borrar históricos.
    em.active = False
    db.commit()
