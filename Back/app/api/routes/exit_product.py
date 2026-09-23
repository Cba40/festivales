# backend/app/api/routes/exit_product.py
# Salir V1: GET /api/events/{event_id}/products/exit
# Público, igual que el resto de los productos (/products/*).
# S3: filtros determinísticos por destino, modalidad y proximidad (GPS).

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.schemas.exit_product import ExitRecommendationResponse
from app.services.service_interaction_log import log_service_interaction
from src.interfaces.rest.exit_product import get_exit_product_adapter

TransporteLiteral = Literal["peatonal", "vehicular", "transporte"]

router = APIRouter(prefix="/api/events/{event_id}", tags=["Exit Product"])


@router.get("/products/exit", response_model=ExitRecommendationResponse)
async def exit_recommendations(
    event_id: str,
    destination_id: str | None = Query(None),
    mode: TransporteLiteral | None = Query(None),
    latitude: float | None = Query(None, ge=-90.0, le=90.0),
    longitude: float | None = Query(None, ge=-180.0, le=180.0),
    db: AsyncSession = Depends(get_async_db),
):
    now = datetime.now(timezone.utc)

    request_mode_parts = []
    if mode:
        request_mode_parts.append(f"mode={mode}")
    if destination_id:
        request_mode_parts.append(f"destination_id={destination_id}")
    request_mode = "&".join(request_mode_parts) if request_mode_parts else None

    try:
        result = await get_exit_product_adapter(
            db=db,
            event_id=event_id,
            timestamp=now,
            destination_id=destination_id,
            mode=mode,
            latitude=latitude,
            longitude=longitude,
        )
    except Exception:
        await log_service_interaction(
            event_id=event_id,
            timestamp=now,
            service_category="exit",
            result_status="error",
            result_count=0,
            zone_ids=[],
            request_mode=request_mode,
        )
        raise

    zonas = result.zonas or []
    await log_service_interaction(
        event_id=event_id,
        timestamp=now,
        service_category="exit",
        result_status="ok" if zonas else "empty",
        result_count=len(zonas),
        zone_ids=[z.zone_id for z in zonas],
        request_mode=request_mode,
    )

    return result
