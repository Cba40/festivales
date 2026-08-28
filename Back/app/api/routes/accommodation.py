from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.models.accommodation import AccommodationType
from app.schemas.accommodation import AccommodationRecommendationResponse
from src.interfaces.rest.accommodation_product import get_accommodation_product_adapter

router = APIRouter(prefix="/api/events/{event_id}", tags=["Accommodation Product"])


@router.get("/products/accommodation", response_model=AccommodationRecommendationResponse)
async def accommodation_recommendations(
    event_id: str,
    type: AccommodationType | None = Query(None),
    latitude: float | None = Query(None, ge=-90.0, le=90.0),
    longitude: float | None = Query(None, ge=-180.0, le=180.0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """Recomendaciones determinísticas de alojamiento para un evento.

    Filtra por tipo canónico (``AccommodationType``), calcula distancia
    Haversine si se proveen coordenadas y ordena por distancia o nombre.
    """
    result = await get_accommodation_product_adapter(
        db=db,
        event_id=event_id,
        acc_type=type,
        user_latitude=latitude,
        user_longitude=longitude,
        limit=limit,
    )

    return result
