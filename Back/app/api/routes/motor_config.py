from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_token
from app.crud.motor_config import (
    get_recommendation_config as crud_get_recommendation_config,
    get_stage4_config as crud_get_stage4_config,
    update_recommendation_config as crud_update_recommendation_config,
    update_stage4_config as crud_update_stage4_config,
)
from app.db.session import get_async_db
from app.schemas.motor_config import (
    RecommendationConfigRead,
    RecommendationConfigUpdate,
    Stage4ConfigRead,
    Stage4ConfigUpdate,
)

router = APIRouter(prefix="/api", tags=["Motor Config"])


@router.get("/recommendation-config", response_model=RecommendationConfigRead)
async def get_recommendation_config(
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await crud_get_recommendation_config(db)


@router.put("/recommendation-config", response_model=RecommendationConfigRead)
async def update_recommendation_config(
    obj_in: RecommendationConfigUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await crud_update_recommendation_config(db, obj_in)


@router.get("/stage4-config", response_model=Stage4ConfigRead)
async def get_stage4_config(
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await crud_get_stage4_config(db)


@router.put("/stage4-config", response_model=Stage4ConfigRead)
async def update_stage4_config(
    obj_in: Stage4ConfigUpdate,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    return await crud_update_stage4_config(db, obj_in)
