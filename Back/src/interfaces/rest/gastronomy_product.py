from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.product import (
    GastronomyRecommendationResponse,
    ZonaGastronomicaItem,
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


def _extra_gastronomy_fields(row) -> dict:
    categoria = ""
    if row.subtipo in ("rapido", "comida", "bebida"):
        categoria = row.subtipo
    return {"categoria": categoria}


async def get_gastronomy_product_adapter(
    db: AsyncSession,
    *,
    timestamp: datetime,
    event_id: str,
    user_context,
    mobility_context,
    limit: int = 5,
) -> GastronomyRecommendationResponse:
    zone_type_map = await load_zone_type_map(db)
    gastronomy_zone_ids = await load_type_filtered_zone_ids(
        db, event_id, zone_type_map, "gastronomy", "comida"
    )

    if not gastronomy_zone_ids:
        return GastronomyRecommendationResponse(
            event_id=event_id,
            timestamp=timestamp.isoformat(),
            mode="sin_solucion",
            zonas=[],
        )

    requested_action = RequestedAction(action_type=ActionType.SEEK_FOOD)

    recs, prediction = await get_recommendations_adapter(
        db=db,
        timestamp=timestamp,
        event_id=event_id,
        user_context=user_context,
        mobility_context=mobility_context,
        requested_action=requested_action,
        limit=limit,
    )

    gastronomy_recs = [r for r in recs if r.zone_id in gastronomy_zone_ids]
    gastronomy_recs = gastronomy_recs[:limit]

    zone_meta = await load_zone_metadata(
        db, [r.zone_id for r in gastronomy_recs],
        extra_fields_fn=_extra_gastronomy_fields,
    )

    zone_states_by_id: dict[UUID, ZoneState] = {}
    if prediction is not None:
        for zs in prediction.zone_states:
            zone_states_by_id[zs.zone_id] = zs

    enriched: list[ZonaGastronomicaItem] = []
    for rec in gastronomy_recs:
        state = zone_states_by_id.get(rec.zone_id)
        meta = zone_meta.get(rec.zone_id)
        extra = {"categoria": meta.get("categoria", "")} if meta else {}
        enriched.append(enrich_zone(rec, state, meta, ZonaGastronomicaItem, extra))

    mode = compute_mode([z.estado for z in enriched])

    return GastronomyRecommendationResponse(
        event_id=event_id,
        timestamp=prediction.timestamp.isoformat()
        if prediction is not None
        else timestamp.isoformat(),
        mode=mode,
        zonas=enriched,
    )
