from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.schemas.product import GastronomyRecommendationResponse
from app.services.service_interaction_log import log_service_interaction
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.interfaces.rest.gastronomy_product import get_gastronomy_product_adapter

router = APIRouter(prefix="/api/events/{event_id}", tags=["Gastronomy Product"])


@router.get("/products/gastronomy", response_model=GastronomyRecommendationResponse)
async def gastronomy_recommendations(
    event_id: str,
    speed: float = Query(..., ge=0.0),
    accessibility_required: bool = Query(...),
    limit: int = Query(5, ge=1, le=50),
    current_zone_id: str | None = Query(None),
    user_id: str = Query(...),
    access_level: AccessLevel = Query(default=AccessLevel.STANDARD),
    latitude: float | None = Query(None, ge=-90.0, le=90.0),
    longitude: float | None = Query(None, ge=-180.0, le=180.0),
    db: AsyncSession = Depends(get_async_db),
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
        latitude=latitude,
        longitude=longitude,
    )

    try:
        result = await get_gastronomy_product_adapter(
            db=db,
            timestamp=now,
            event_id=event_id,
            user_context=user_ctx,
            mobility_context=mobility_ctx,
            limit=limit,
        )
    except Exception:
        await log_service_interaction(
            event_id=event_id,
            timestamp=now,
            service_category="gastronomy",
            result_status="error",
            result_count=0,
            zone_ids=[],
        )
        raise

    zonas = result.zonas or []
    await log_service_interaction(
        event_id=event_id,
        timestamp=now,
        service_category="gastronomy",
        result_status="ok" if zonas else "empty",
        result_count=len(zonas),
        zone_ids=[z.zone_id for z in zonas],
        request_mode=None,
    )

    return result
