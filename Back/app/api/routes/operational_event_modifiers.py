"""Endpoints for OperationalEventModifier."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_token
from app.crud import (
    create_operational_event_modifier,
    delete_operational_event_modifier,
    get_operational_event_modifier,
    list_by_event_type,
    update_operational_event_modifier,
)
from app.db.session import get_async_db
from app.schemas.operational_event_modifier import (
    OperationalEventModifierCreate,
    OperationalEventModifierResponse,
    OperationalEventModifierUpdate,
)

router = APIRouter(prefix="/operational-event-modifiers", tags=["Operational Event Modifiers"])


@router.post("/", response_model=OperationalEventModifierResponse, status_code=status.HTTP_201_CREATED)
async def create(
    obj_in: OperationalEventModifierCreate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    try:
        return await create_operational_event_modifier(db, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.get("/{modifier_id}", response_model=OperationalEventModifierResponse)
async def get_by_id(
    modifier_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    db_obj = await get_operational_event_modifier(db, modifier_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OperationalEventModifier not found")
    return db_obj


@router.get("/by-event-type/{event_type}", response_model=list[OperationalEventModifierResponse])
async def list_by_event_type_route(
    event_type: str,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await list_by_event_type(db, event_type)


@router.put("/{modifier_id}", response_model=OperationalEventModifierResponse)
async def update(
    modifier_id: UUID,
    obj_in: OperationalEventModifierUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    db_obj = await get_operational_event_modifier(db, modifier_id)
    if not db_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OperationalEventModifier not found")
    try:
        return await update_operational_event_modifier(db, db_obj, obj_in)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete("/{modifier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    modifier_id: UUID,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    deleted = await delete_operational_event_modifier(db, modifier_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="OperationalEventModifier not found")
