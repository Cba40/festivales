from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_token
from app.db.session import get_async_db
from app.schemas.product import HealthRecommendationResponse
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.interfaces.rest.health_product import get_health_product_adapter

router = APIRouter(prefix="/api/events/{event_id}", tags=["Health Product"])


@router.get("/products/health", response_model=HealthRecommendationResponse)
async def health_recommendations(
    event_id: str,
    speed: float = Query(..., ge=0.0),
    accessibility_required: bool = Query(...),
    limit: int = Query(5, ge=1, le=50),
    current_zone_id: str | None = Query(None),
    user_id: str = Query(...),
    access_level: AccessLevel = Query(default=AccessLevel.STANDARD),
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    now = datetime.now(timezone.utc)

    user_ctx = UserContext(
        user_id=UUID(user_id),
        access_level=access_level,
    )
    mobility_ctx = MobilityContext(
        current_zone_id=UUID(current_zone_id) if current_zone_id else None,
        speed=speed,
        accessibility_required=accessibility_required,
    )

    result = await get_health_product_adapter(
        db=db,
        timestamp=now,
        event_id=event_id,
        user_context=user_ctx,
        mobility_context=mobility_ctx,
        limit=limit,
    )

    return result
