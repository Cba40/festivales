"""Endpoints for OperationalObservation (RFC-006 §4 - Operational Observations)."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_token
from app.crud.operational_observation import (
    create_operational_observation,
    get_operational_observation,
    list_operational_observations,
)
from app.db.session import get_async_db
from app.schemas.operational_observation import (
    OperationalObservationCreate,
    OperationalObservationResponse,
)

router = APIRouter(prefix="/operational-observations", tags=["Operational Observations"])


@router.get("", response_model=list[OperationalObservationResponse])
async def list_observations_endpoint(
    event_day_id: UUID | None = Query(None, description="Filtrar por ID de jornada de evento"),
    zone_id: UUID | None = Query(None, description="Filtrar por ID de zona"),
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    """Listar observaciones operativas con filtros opcionales."""
    return await list_operational_observations(db, event_day_id, zone_id)


@router.get("/{observation_id}", response_model=OperationalObservationResponse)
async def get_observation_endpoint(
    observation_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    """Obtener una observación operativa por ID."""
    db_obj = await get_operational_observation(db, observation_id)
    if not db_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OperationalObservation not found",
        )
    return db_obj


@router.post("", response_model=OperationalObservationResponse, status_code=status.HTTP_201_CREATED)
async def create_observation_endpoint(
    obj_in: OperationalObservationCreate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    """Registrar una nueva observación operativa."""
    try:
        return await create_operational_observation(db, obj_in)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )