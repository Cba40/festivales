# backend/app/api/routes/exit_product.py
# S2 (Salir V1): GET /api/events/{event_id}/products/exit
# Público, igual que el resto de los productos (/products/*).

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.schemas.exit_product import ExitRecommendationResponse
from src.interfaces.rest.exit_product import get_exit_product_adapter

router = APIRouter(prefix="/api/events/{event_id}", tags=["Exit Product"])


@router.get("/products/exit", response_model=ExitRecommendationResponse)
async def exit_recommendations(
    event_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    return await get_exit_product_adapter(
        db=db,
        event_id=event_id,
        timestamp=datetime.now(timezone.utc),
    )
