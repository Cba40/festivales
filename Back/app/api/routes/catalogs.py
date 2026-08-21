from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import verify_token
from app.crud.zone_subtype import zone_subtype as zone_subtype_crud
from app.crud.zone_type import zone_type as zone_type_crud
from app.db.session import get_db
from app.schemas.zone_subtype import ZoneSubtypeResponse
from app.schemas.zone_type import ZoneTypeResponse

router = APIRouter(prefix="/api/context-engine", tags=["context-engine"])


@router.get("/zone-types", response_model=list[ZoneTypeResponse])
def get_zone_types(
    db: Session = Depends(get_db),
    _: None = Depends(verify_token),
):
    """Return all ZoneTypes."""
    return zone_type_crud.get_multi(db)


@router.get("/zone-subtypes", response_model=list[ZoneSubtypeResponse])
def get_zone_subtypes(
    zone_type_id: Optional[str] = Query(
        default=None,
        description="Filtra subtipos de un tipo de zona (id). Si se omite, devuelve todos.",
    ),
    only_active: bool = Query(
        default=True,
        description="Si es true, devuelve solo los subtipos activos.",
    ),
    db: Session = Depends(get_db),
    _: None = Depends(verify_token),
):
    """Return all ZoneSubtypes (opcionalmente filtrados por tipo), ordenados por sort_order y name."""
    return zone_subtype_crud.get_multi(
        db, zone_type_id=zone_type_id, only_active=only_active
    )
