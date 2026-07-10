"""Endpoints for ZoneBehavior."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_token
from app.crud import (
    create_zone_behavior,
    delete_zone_behavior,
    get_zone_behavior,
    list_zone_behaviors_by_phase,
    update_zone_behavior,
)
from app.db.session import get_async_db
from app.schemas.zone_behavior import (
    ZoneBehaviorCreate,
    ZoneBehaviorResponse,
    ZoneBehaviorUpdate,
)

router = APIRouter(prefix="/zone-behaviors", tags=["Zone Behaviors"])


@router.post("/", response_model=ZoneBehaviorResponse, status_code=status.HTTP_201_CREATED)
async def create(
    obj_in: ZoneBehaviorCreate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    try:
        return await create_zone_behavior(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/{behavior_id}", response_model=ZoneBehaviorResponse)
async def get_by_id(
    behavior_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    db_obj = await get_zone_behavior(db, behavior_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ZoneBehavior not found")
    return db_obj


@router.get("/by-phase/{phase_id}", response_model=list[ZoneBehaviorResponse])
async def list_by_phase(
    phase_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await list_zone_behaviors_by_phase(db, phase_id)


@router.put("/{behavior_id}", response_model=ZoneBehaviorResponse)
async def update(
    behavior_id: UUID,
    obj_in: ZoneBehaviorUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    db_obj = await get_zone_behavior(db, behavior_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ZoneBehavior not found")
    try:
        return await update_zone_behavior(db, db_obj, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete("/{behavior_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    behavior_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    deleted = await delete_zone_behavior(db, behavior_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ZoneBehavior not found")
