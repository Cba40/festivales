from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_async_db
from app.models.city import City
from app.models.emergency import EmergencyType
from app.schemas.emergency import EmergencyRecommendationResponse
from app.schemas.emergency_admin import CityResponse
from src.interfaces.rest.emergency_product import get_emergency_product_adapter

router = APIRouter(prefix="/api", tags=["Emergency"])


@router.get("/cities", response_model=list[CityResponse])
async def list_cities(
    db: AsyncSession = Depends(get_async_db),
):
    """Lista las ciudades disponibles (público) para el módulo de emergencias.

    Permite que ``<EmergencyModule />`` se auto-descubra: sin un ``city_id``
    explícito, la app pública consulta esta ruta y usa la primera ciudad
    disponible, sin depender de configuración externa.
    """
    result = await db.execute(select(City).order_by(City.name))
    return result.scalars().all()


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
