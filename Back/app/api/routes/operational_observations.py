from fastapi import APIRouter, Depends
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.operational_observation import create_observation, find_by_zone_and_date_range
from app.db.session import get_async_db
from app.schemas.operational_observation import OperationalObservationCreate, OperationalObservationResponse


router = APIRouter(prefix="/operational-observations", tags=["operational-observations"])


@router.post("/", response_model=OperationalObservationResponse)
async def create_observation_endpoint(
    observation_in: OperationalObservationCreate,
    db: AsyncSession = Depends(get_async_db),
):
    result = await create_observation(db, observation_in)
    return result


@router.get("/", response_model=list[OperationalObservationResponse])
async def list_by_zone_and_date(
    zone_id: str,
    start: datetime,
    end: datetime,
    db: AsyncSession = Depends(get_async_db),
):
    result = await find_by_zone_and_date_range(db, zone_id, start, end)
    return result