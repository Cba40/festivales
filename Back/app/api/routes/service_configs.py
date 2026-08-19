"""CRUD HTTP de `service_configs` (permanencias de servicios por tipo de zona).

Permite administrar los defaults globales (event_day_id NULL) y los overrides
por jornada (event_day_id seteado). La unicidad sigue los índices de la tabla:
un solo default y un solo override por (zone_type_id, subtipo).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TokenPayload, verify_token
from app.db.session import get_async_db
from app.models.service_config import ServiceConfig
from app.schemas.service_config import (
    ServiceConfigCreate,
    ServiceConfigRead,
    ServiceConfigUpdate,
)

router = APIRouter(prefix="/api/service-configs", tags=["Service Config"])


def _subtipokey(subtipo: str | None) -> str:
    return subtipo or ""


async def _exists(
    db: AsyncSession, zone_type_id: str, subtipo: str | None, event_day_id: str | None
) -> bool:
    stmt = select(ServiceConfig.id).where(
        ServiceConfig.zone_type_id == zone_type_id,
        func.coalesce(ServiceConfig.subtipo, "") == _subtipokey(subtipo),
        ServiceConfig.event_day_id.is_(None)
        if event_day_id is None
        else ServiceConfig.event_day_id == event_day_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def _get_or_404(db: AsyncSession, config_id: str) -> ServiceConfig:
    result = await db.execute(select(ServiceConfig).where(ServiceConfig.id == config_id))
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ServiceConfig no encontrada",
        )
    return config


@router.get("", response_model=list[ServiceConfigRead])
async def list_service_configs(
    zone_type_id: str | None = Query(default=None, description="Filtra por tipo de zona"),
    subtipo: str | None = Query(default=None, description="Filtra por subtipo"),
    event_day_id: str | None = Query(
        default=None,
        description="Si se omite, lista los defaults (event_day_id NULL); si se indica, los overrides de esa jornada",
    ),
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    filters = []
    if zone_type_id is not None:
        filters.append(ServiceConfig.zone_type_id == zone_type_id)
    if subtipo is not None:
        filters.append(func.coalesce(ServiceConfig.subtipo, "") == _subtipokey(subtipo))
    if event_day_id is None:
        filters.append(ServiceConfig.event_day_id.is_(None))
    else:
        filters.append(ServiceConfig.event_day_id == event_day_id)
    stmt = (
        select(ServiceConfig)
        .where(*filters)
        .order_by(
            ServiceConfig.zone_type_id,
            ServiceConfig.subtipo,
            ServiceConfig.event_day_id,
            ServiceConfig.id,
        )
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=ServiceConfigRead, status_code=status.HTTP_201_CREATED)
async def create_service_config(
    obj_in: ServiceConfigCreate,
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    subtipo = obj_in.subtipo or None
    if await _exists(db, obj_in.zone_type_id, subtipo, obj_in.event_day_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un ServiceConfig para (zone_type_id, subtipo, event_day_id)",
        )
    config = ServiceConfig(
        id=str(uuid.uuid4()),
        zone_type_id=obj_in.zone_type_id,
        subtipo=subtipo,
        event_day_id=obj_in.event_day_id,
        average_duration_min=obj_in.average_duration_min,
    )
    db.add(config)
    await db.commit()
    await db.refresh(config)
    return config


@router.put("/{config_id}", response_model=ServiceConfigRead)
async def update_service_config(
    config_id: str,
    obj_in: ServiceConfigUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    config = await _get_or_404(db, config_id)
    config.average_duration_min = obj_in.average_duration_min
    await db.commit()
    await db.refresh(config)
    return config


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_config(
    config_id: str,
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    config = await _get_or_404(db, config_id)
    await db.delete(config)
    await db.commit()