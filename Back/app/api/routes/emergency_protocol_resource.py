"""Endpoint público de resolución de recursos (Emergencia V2 - S3).

Expone ``GET /api/emergency-protocols/recommended-resource``: dado un
``target_type`` de protocolo y una ciudad, devuelve el recurso ``Emergency``
recomendado (determinístico). Permite opcionalmente GPS para priorizar por
distancia Haversine. Público: async, ``get_async_db``, sin ``verify_token``.

La composición protocolo → recurso se delega al adapter puro
``src/interfaces/rest/emergency_protocol_resource_resolver``.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.models.emergency import Emergency, EmergencyType
from app.schemas.emergency_admin import EmergencyResponse
from src.interfaces.rest.emergency_protocol_resource_resolver import (
    resolve_recommended_resource,
)

router = APIRouter(prefix="/api", tags=["EmergencyProtocolResource"])


@router.get(
    "/emergency-protocols/recommended-resource",
    response_model=EmergencyResponse,
)
async def recommended_resource(
    target_type: EmergencyType = Query(...),
    city_id: UUID = Query(...),
    latitude: float | None = Query(None),
    longitude: float | None = Query(None),
    db: AsyncSession = Depends(get_async_db),
):
    """Recurso territorial recomendado para un target_type y ciudad.

    Resuelve el ``Emergency`` activo del tipo pedido en la ciudad indicada,
    priorizando el más cercano al GPS (si se provee) o alfabético (si no).
    Sin recurso compatible → 404.
    """
    result = await db.execute(select(Emergency))
    rows = result.scalars().all()

    resource = resolve_recommended_resource(
        target_type=target_type,
        city_id=str(city_id),
        emergencies=rows,
        latitude=latitude,
        longitude=longitude,
    )

    if resource is None:
        raise HTTPException(status_code=404, detail="No hay recurso compatible disponible")

    return resource