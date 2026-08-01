# Health Product Endpoint
#
# Visitor intent:
#   Health assistance.
#
# Domain classification:
#   Security.
#
# This endpoint adapts the Security domain model to the Health product experience.

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.product import (
    HealthRecommendationResponse,
    ZonaSaludItem,
)
from src.domain.recommendation.requested_action import (
    ActionType,
    RequestedAction,
)
from src.domain.value_objects.zone_state import ZoneState
from src.interfaces.rest.product_helpers import (
    compute_mode,
    enrich_zone,
    load_zone_metadata,
)
from src.interfaces.rest.recommendations import get_recommendations_adapter


async def get_health_product_adapter(
    db: AsyncSession,
    *,
    timestamp: datetime,
    event_id: str,
    user_context,
    mobility_context,
    limit: int = 5,
) -> HealthRecommendationResponse:
    requested_action = RequestedAction(action_type=ActionType.SEEK_SECURITY)

    recs, prediction = await get_recommendations_adapter(
        db=db,
        timestamp=timestamp,
        event_id=event_id,
        user_context=user_context,
        mobility_context=mobility_context,
        requested_action=requested_action,
        limit=limit,
    )

    zone_meta = await load_zone_metadata(
        db, [r.zone_id for r in recs],
    )

    zone_states_by_id: dict[UUID, ZoneState] = {}
    if prediction is not None:
        for zs in prediction.zone_states:
            zone_states_by_id[zs.zone_id] = zs

    enriched: list[ZonaSaludItem] = []
    for rec in recs:
        state = zone_states_by_id.get(rec.zone_id)
        meta = zone_meta.get(rec.zone_id)
        enriched.append(enrich_zone(rec, state, meta, ZonaSaludItem))

    mode = compute_mode([z.estado for z in enriched])

    return HealthRecommendationResponse(
        event_id=event_id,
        timestamp=prediction.timestamp.isoformat()
        if prediction is not None
        else timestamp.isoformat(),
        mode=mode,
        zonas=enriched,
    )
