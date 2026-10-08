from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.zone_subtype import ZoneSubtype
from app.models.zone_type import ZoneType
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
    load_zone_metadata,
)
from src.interfaces.rest.recommendations import get_recommendations_adapter

# Tipo de zona del catálogo al que cuelgan los subtipos de gastronomía.
# Debe coincidir con `ActionType.SEEK_FOOD -> ("comida", None)` en
# `requested_action.py` y con el slug sembrado por la migración b0c1d2e3f4a5.
GASTRONOMY_ZONE_TYPE_SLUG = "comida"


async def _load_gastronomy_subtipos(db: AsyncSession) -> frozenset[str]:
    """Subtipos activos de gastronomía, leídos del catálogo.

    Antes esta lista estaba fija en el código. Eso obligaba a tocar el módulo
    cada vez que una migración agregaba un subtipo, y si se olvidaba el
    subtipo nuevo pasaba con `categoria=""` en silencio. Ahora sale de
    `zone_subtypes`, que es la fuente de verdad.
    """
    stmt = (
        select(ZoneSubtype.slug)
        .join(ZoneType, ZoneType.id == ZoneSubtype.zone_type_id)
        .where(ZoneType.slug == GASTRONOMY_ZONE_TYPE_SLUG)
        .where(ZoneSubtype.is_active.is_(True))
    )
    return frozenset((await db.execute(stmt)).scalars().all())


def _gastronomy_fields_fn(
    subtipos: frozenset[str],
):
    """Construye el `extra_fields_fn` de `load_zone_metadata`."""

    def _extra_gastronomy_fields(row) -> dict:
        categoria = row.subtipo if row.subtipo in subtipos else ""
        return {"categoria": categoria}

    return _extra_gastronomy_fields


async def get_gastronomy_product_adapter(
    db: AsyncSession,
    *,
    timestamp: datetime,
    event_id: str,
    user_context,
    mobility_context,
    limit: int = 5,
    event_day_id: str | None = None,
) -> GastronomyRecommendationResponse:
    requested_action = RequestedAction(action_type=ActionType.SEEK_FOOD)

    recs, prediction = await get_recommendations_adapter(
        db=db,
        timestamp=timestamp,
        event_id=event_id,
        user_context=user_context,
        mobility_context=mobility_context,
        requested_action=requested_action,
        limit=limit,
        event_day_id=event_day_id,
    )

    zone_meta = await load_zone_metadata(
        db,
        [r.zone_id for r in recs],
        extra_fields_fn=_gastronomy_fields_fn(
            await _load_gastronomy_subtipos(db)
        ),
    )

    zone_states_by_id: dict[UUID, ZoneState] = {}
    if prediction is not None:
        for zs in prediction.zone_states:
            zone_states_by_id[zs.zone_id] = zs

    enriched: list[ZonaGastronomicaItem] = []
    for rec in recs:
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
