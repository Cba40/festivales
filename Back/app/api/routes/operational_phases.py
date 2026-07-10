"""Endpoints for OperationalPhase."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_token
from app.crud import (
    create_operational_phase,
    delete_operational_phase,
    get_operational_phase,
    list_phases_by_profile,
    update_operational_phase,
)
from app.db.session import get_async_db
from app.schemas.operational_phase import (
    OperationalPhaseCreate,
    OperationalPhaseResponse,
    OperationalPhaseUpdate,
)

router = APIRouter(prefix="/operational-phases", tags=["Operational Phases"])


@router.post("/", response_model=OperationalPhaseResponse, status_code=status.HTTP_201_CREATED)
async def create(
    obj_in: OperationalPhaseCreate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    try:
        return await create_operational_phase(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/{phase_id}", response_model=OperationalPhaseResponse)
async def get_by_id(
    phase_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    db_obj = await get_operational_phase(db, phase_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OperationalPhase not found")
    return db_obj


@router.get("/by-profile/{profile_id}", response_model=list[OperationalPhaseResponse])
async def list_by_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await list_phases_by_profile(db, profile_id)


@router.put("/{phase_id}", response_model=OperationalPhaseResponse)
async def update(
    phase_id: UUID,
    obj_in: OperationalPhaseUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    db_obj = await get_operational_phase(db, phase_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OperationalPhase not found")
    try:
        return await update_operational_phase(db, db_obj, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete("/{phase_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    phase_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    deleted = await delete_operational_phase(db, phase_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OperationalPhase not found")
