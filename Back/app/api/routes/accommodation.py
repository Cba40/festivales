from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.models.accommodation import AccommodationType
from app.schemas.accommodation import AccommodationRecommendationResponse
from app.services.service_interaction_log import (
    REQUEST_ORIGIN_HEADER,
    log_service_interaction,
    resolve_request_origin,
)
from src.interfaces.rest.accommodation_product import get_accommodation_product_adapter

router = APIRouter(prefix="/api/events/{event_id}", tags=["Accommodation Product"])


@router.get("/products/accommodation", response_model=AccommodationRecommendationResponse)
async def accommodation_recommendations(
    event_id: str,
    type: AccommodationType | None = Query(None),
    latitude: float | None = Query(None, ge=-90.0, le=90.0),
    longitude: float | None = Query(None, ge=-180.0, le=180.0),
    limit: int = Query(20, ge=1, le=100),
    x_request_origin: str | None = Header(default=None, alias=REQUEST_ORIGIN_HEADER),
    db: AsyncSession = Depends(get_async_db),
):
    """Recomendaciones determinísticas de alojamiento para un evento.

    Filtra por tipo canónico (``AccommodationType``), calcula distancia
    Haversine si se proveen coordenadas y ordena por distancia o nombre.
    """
    now = datetime.now(timezone.utc)
    origin = resolve_request_origin(x_request_origin)

    request_mode = None
    if type is not None:
        request_mode = f"type={type.value}"

    try:
        result = await get_accommodation_product_adapter(
            db=db,
            event_id=event_id,
            acc_type=type,
            user_latitude=latitude,
            user_longitude=longitude,
            limit=limit,
        )
    except Exception:
        await log_service_interaction(
            event_id=event_id,
            timestamp=now,
            service_category="accommodation",
            result_status="error",
            result_count=0,
            zone_ids=[],
            request_mode=request_mode,
            origin=origin,
        )
        raise

    accommodations = result.accommodations or []
    await log_service_interaction(
        event_id=event_id,
        timestamp=now,
        service_category="accommodation",
        result_status="ok" if accommodations else "empty",
        result_count=len(accommodations),
        zone_ids=[],
        request_mode=request_mode,
        origin=origin,
    )

    return result
