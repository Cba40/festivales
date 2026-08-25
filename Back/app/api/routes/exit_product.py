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
    return await get_exit_product_adapter(
        db=db,
        event_id=event_id,
        timestamp=datetime.now(timezone.utc),
        destination_id=destination_id,
        mode=mode,
        latitude=latitude,
        longitude=longitude,
    )
