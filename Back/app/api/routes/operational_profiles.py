"""Endpoints for OperationalProfile."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_token
from app.crud import (
    create_operational_profile,
    delete_operational_profile,
    get_operational_profile,
    list_profiles,
    update_operational_profile,
)
from app.db.session import get_async_db
from app.schemas.operational_profile import (
    OperationalProfileCreate,
    OperationalProfileResponse,
    OperationalProfileUpdate,
)

router = APIRouter(prefix="/operational-profiles", tags=["Operational Profiles"])


@router.post("/", response_model=OperationalProfileResponse, status_code=status.HTTP_201_CREATED)
async def create(
    obj_in: OperationalProfileCreate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    try:
        return await create_operational_profile(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/{profile_id}", response_model=OperationalProfileResponse)
async def get_by_id(
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    db_obj = await get_operational_profile(db, profile_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OperationalProfile not found")
    return db_obj


@router.get("/", response_model=list[OperationalProfileResponse])
async def list_all(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await list_profiles(db, skip=skip, limit=limit)


@router.put("/{profile_id}", response_model=OperationalProfileResponse)
async def update(
    profile_id: UUID,
    obj_in: OperationalProfileUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    db_obj = await get_operational_profile(db, profile_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OperationalProfile not found")
    try:
        return await update_operational_profile(db, db_obj, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    profile_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    deleted = await delete_operational_profile(db, profile_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OperationalProfile not found")
