from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.models.transport_line import TransportLine
from app.models.transport_line_stop import TransportLineStop
from app.models.transport_schedule import TransportSchedule
from app.schemas.product import TransportRecommendationResponse
from app.services.service_interaction_log import (
    REQUEST_ORIGIN_HEADER,
    log_service_interaction,
    resolve_request_origin,
)
from src.interfaces.rest.transport_product import get_transport_product_adapter

router = APIRouter(prefix="/api/events/{event_id}", tags=["Transport Product"])


@router.get("/transport/destinations")
async def get_available_destinations(
    event_id: str,
    transport_type: str | None = Query(None, pattern="^(urbano|interurbano)$"),
    db: AsyncSession = Depends(get_async_db),
):
    """Devuelve destinos únicos disponibles, opcionalmente filtrados por tipo."""
    stmt = (
        select(TransportSchedule.destination)
        .distinct()
        .join(TransportLineStop, TransportLineStop.id == TransportSchedule.line_stop_id)
        .join(TransportLine, TransportLine.id == TransportLineStop.line_id)
        .where(TransportLine.event_id == event_id)
        .where(TransportLine.active == True)
    )
    if transport_type:
        stmt = stmt.where(TransportLine.type == transport_type)
    stmt = stmt.order_by(TransportSchedule.destination)
    result = await db.execute(stmt)
    return {"destinations": [row[0] for row in result.all()]}


@router.get("/products/transport", response_model=TransportRecommendationResponse)
async def transport_recommendations(
    event_id: str,
    destination: str | None = Query(None),
    transport_type: str | None = Query(None, pattern="^(urbano|interurbano)$"),
    latitude: float | None = Query(None, ge=-90.0, le=90.0),
    longitude: float | None = Query(None, ge=-180.0, le=180.0),
    limit: int = Query(5, ge=1, le=50),
    speed: float | None = Query(None, ge=0.0),
    accessibility_required: bool = Query(False),
    user_id: str | None = Query(None),
    access_level: str | None = Query(None),
    current_zone_id: str | None = Query(None),
    x_request_origin: str | None = Header(default=None, alias=REQUEST_ORIGIN_HEADER),
    db: AsyncSession = Depends(get_async_db),
):
    now = datetime.now(timezone.utc)
    origin = resolve_request_origin(x_request_origin)

    request_mode_parts = []
    if transport_type:
        request_mode_parts.append(f"transport_type={transport_type}")
    if destination:
        request_mode_parts.append(f"destination={destination}")
    request_mode = "&".join(request_mode_parts) if request_mode_parts else None

    try:
        result = await get_transport_product_adapter(
            db=db,
            timestamp=now,
            event_id=event_id,
            destination=destination,
            transport_type=transport_type,
            user_latitude=latitude,
            user_longitude=longitude,
            limit=limit,
        )
    except Exception:
        await log_service_interaction(
            event_id=event_id,
            timestamp=now,
            service_category="transport",
            result_status="error",
            result_count=0,
            zone_ids=[],
            request_mode=request_mode,
            origin=origin,
        )
        raise

    zonas = result.zonas or []
    await log_service_interaction(
        event_id=event_id,
        timestamp=now,
        service_category="transport",
        result_status="ok" if zonas else "empty",
        result_count=len(zonas),
        zone_ids=[z.zone_id for z in zonas],
        request_mode=request_mode,
        origin=origin,
    )

    return result
