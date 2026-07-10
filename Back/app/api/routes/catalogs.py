from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import verify_token
from app.crud import zone_type as zone_type_crud
from app.db.session import get_db
from app.schemas.zone_type import ZoneTypeResponse

router = APIRouter(prefix="/api/context-engine", tags=["context-engine"])


@router.get("/zone-types", response_model=list[ZoneTypeResponse])
def get_zone_types(
    db: Session = Depends(get_db),
    _: None = Depends(verify_token),
):
    """Return all ZoneTypes."""
    return zone_type_crud.get_multi(db)
