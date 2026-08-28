from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.models.emergency import EmergencyType
from app.schemas.emergency import EmergencyRecommendationResponse
from src.interfaces.rest.emergency_product import get_emergency_product_adapter

router = APIRouter(prefix="/api", tags=["Emergency"])


@router.get("/emergencies", response_model=EmergencyRecommendationResponse)
async def emergency_recommendations(
    city_id: UUID = Query(...),
    type: EmergencyType | None = Query(None),
    latitude: float | None = Query(None, ge=-90.0, le=90.0),
    longitude: float | None = Query(None, ge=-180.0, le=180.0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """Recomendaciones determinísticas de emergencias de una ciudad.

    Filtra por tipo canónico (``EmergencyType``), calcula distancia Haversine si
    se proveen coordenadas y ordena por distancia (con GPS) o por nombre (sin
    GPS). Las emergencias sin ubicación (números como 911 / 107 / 100) se listan
    al final con ``distance_km = None``.
    """
    result = await get_emergency_product_adapter(
        db=db,
        city_id=str(city_id),
        emergency_type=type,
        user_latitude=latitude,
        user_longitude=longitude,
        limit=limit,
    )

    return result
