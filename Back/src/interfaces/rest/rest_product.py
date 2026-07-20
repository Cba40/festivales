from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.product import (
    RestRecommendationResponse,
    ZonaRestItem,
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


async def get_rest_product_adapter(
    db: AsyncSession,
    *,
    timestamp: datetime,
    event_id: str,
    user_context,
    mobility_context,
    limit: int = 5,
) -> RestRecommendationResponse:
    zone_type_map = await load_zone_type_map(db)
    rest_zone_ids = await load_type_filtered_zone_ids(
        db, event_id, zone_type_map, "RestArea", "servicios", subtype="descanso"
    )

    if not rest_zone_ids:
        return RestRecommendationResponse(
            event_id=event_id,
            timestamp=timestamp.isoformat(),
            mode="sin_solucion",
            zonas=[],
        )

    requested_action = RequestedAction(action_type=ActionType.SEEK_REST)

    recs, prediction = await get_recommendations_adapter(
        db=db,
        timestamp=timestamp,
        event_id=event_id,
        user_context=user_context,
        mobility_context=mobility_context,
        requested_action=requested_action,
        limit=limit,
    )

    rest_recs = [r for r in recs if r.zone_id in rest_zone_ids]
    rest_recs = rest_recs[:limit]

    zone_meta = await load_zone_metadata(
        db, [r.zone_id for r in rest_recs],
    )

    zone_states_by_id: dict[UUID, ZoneState] = {}
    if prediction is not None:
        for zs in prediction.zone_states:
            zone_states_by_id[zs.zone_id] = zs

    enriched: list[ZonaRestItem] = []
    for rec in rest_recs:
        state = zone_states_by_id.get(rec.zone_id)
        meta = zone_meta.get(rec.zone_id)
        enriched.append(enrich_zone(rec, state, meta, ZonaRestItem))

    mode = compute_mode([z.estado for z in enriched])

    return RestRecommendationResponse(
        event_id=event_id,
        timestamp=prediction.timestamp.isoformat()
        if prediction is not None
        else timestamp.isoformat(),
        mode=mode,
        zonas=enriched,
    )
