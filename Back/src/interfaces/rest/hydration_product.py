from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.product import (
    HydrationRecommendationResponse,
    ZonaHidratacionItem,
)
from src.domain.recommendation.requested_action import (
    ActionType,
    RequestedAction,
)
from src.domain.value_objects.zone_state import ZoneState
from src.interfaces.rest.product_helpers import (
    compute_mode,
    enrich_zone,
    load_type_filtered_zone_ids,
    load_zone_metadata,
    load_zone_type_map,
)
from src.interfaces.rest.recommendations import get_recommendations_adapter


async def get_hydration_product_adapter(
    db: AsyncSession,
    *,
    timestamp: datetime,
    event_id: str,
    user_context,
    mobility_context,
    limit: int = 5,
) -> HydrationRecommendationResponse:
    zone_type_map = await load_zone_type_map(db)
    hydration_zone_ids = await load_type_filtered_zone_ids(
        db, event_id, zone_type_map, "Information", "servicios", subtype="hidratacion"
    )

    if not hydration_zone_ids:
        return HydrationRecommendationResponse(
            event_id=event_id,
            timestamp=timestamp.isoformat(),
            mode="sin_solucion",
            zonas=[],
        )

    requested_action = RequestedAction(action_type=ActionType.SEEK_HYDRATION)

    recs, prediction = await get_recommendations_adapter(
        db=db,
        timestamp=timestamp,
        event_id=event_id,
        user_context=user_context,
        mobility_context=mobility_context,
        requested_action=requested_action,
        limit=limit,
    )

    hydration_recs = [r for r in recs if r.zone_id in hydration_zone_ids]
    hydration_recs = hydration_recs[:limit]

    zone_meta = await load_zone_metadata(
        db, [r.zone_id for r in hydration_recs],
    )

    zone_states_by_id: dict[UUID, ZoneState] = {}
    if prediction is not None:
        for zs in prediction.zone_states:
            zone_states_by_id[zs.zone_id] = zs

    enriched: list[ZonaHidratacionItem] = []
    for rec in hydration_recs:
        state = zone_states_by_id.get(rec.zone_id)
        meta = zone_meta.get(rec.zone_id)
        enriched.append(enrich_zone(rec, state, meta, ZonaHidratacionItem))

    mode = compute_mode([z.estado for z in enriched])

    return HydrationRecommendationResponse(
        event_id=event_id,
        timestamp=prediction.timestamp.isoformat()
        if prediction is not None
        else timestamp.isoformat(),
        mode=mode,
        zonas=enriched,
    )
