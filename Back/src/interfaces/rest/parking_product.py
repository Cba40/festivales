"""REST adapter: composes the enriched Parking Product response.

Reuses get_recommendations_adapter (which delegates to RecommendationModule
→ GetRecommendations) and enriches with ZoneState data and zone metadata.
Composition happens exclusively in this adapter — no domain changes.

Adapter-level heuristics (not part of the domain engine):
  - _saturation_to_estado: thresholds mapping saturation float → category label
  - _compute_mode:     aggregates zone estado to determine display mode
                        (guiar/asistir/informar/sin_solucion per contract §7.1)
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.zone import Zone as ZoneORM
from app.models.zone_type import ZoneType as ZoneTypeORM
from app.schemas.product import (
    ParkingRecommendationResponse,
    ZonaEstacionamientoItem,
)
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import (
    ActionType,
    RequestedAction,
)
from src.domain.recommendation.user_context import UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.interfaces.rest.recommendations import get_recommendations_adapter


def _saturation_to_estado(saturation_level: float) -> str:
    """Adapter heuristic: maps saturation 0.0–1.0 to display category.

    Not produced by the engine — this is a presentation-layer rule
    documented in FRONTEND_BACKEND_CONTRACT.md §7.1 (mockZones).
    """
    if saturation_level < 0.25:
        return "bajo"
    if saturation_level < 0.50:
        return "medio"
    if saturation_level < 0.75:
        return "alto"
    return "colapsado"


def _compute_mode(
    items: list[ZonaEstacionamientoItem],
) -> str:
    """Adapter heuristic: determines display mode from zone saturation.

    Modes (guiar/asistir/informar/sin_solucion) match the approved
    functional model in FRONTEND_BACKEND_CONTRACT.md §7.1 / §12.2 (G-F3).

    This logic lives in the adapter, not the domain engine, because it
    aggregates *presentation* semantics — no business rule is duplicated.
    """
    if not items:
        return "sin_solucion"

    colapsadas = [z for z in items if z.estado == "colapsado"]
    saturadas = [z for z in items if z.estado in ("alto", "colapsado")]

    if len(colapsadas) == len(items):
        return "sin_solucion"
    if len(saturadas) == len(items):
        return "guiar"
    if len(saturadas) > len(items) / 2:
        return "asistir"
    return "informar"


def _enrich_zone(
    rec: ZoneRecommendation,
    state: ZoneState | None,
    meta: dict | None,
) -> ZonaEstacionamientoItem:
    if state is not None:
        saturation_level = state.saturation_level
        availability = state.availability
        estimated_wait = state.estimated_wait
        confidence = state.confidence
        active_restriction = state.active_restriction.value
        operational_state = state.operational_state
    else:
        saturation_level = 0.0
        availability = 0
        estimated_wait = 0
        confidence = 0.0
        active_restriction = "OPEN"
        operational_state = "UNKNOWN"

    estado = _saturation_to_estado(saturation_level)
    disponibilidad = max(0, min(100, round((1.0 - saturation_level) * 100)))

    return ZonaEstacionamientoItem(
        zone_id=str(rec.zone_id),
        name=meta["name"] if meta else str(rec.zone_id),
        score=rec.score,
        reasoning=list(rec.reasoning),
        saturation_level=saturation_level,
        estado=estado,
        availability=availability,
        disponibilidad=disponibilidad,
        estimated_wait=estimated_wait,
        confidence=confidence,
        active_restriction=active_restriction,
        operational_state=operational_state,
        lat=meta["lat"] if meta else None,
        lng=meta["lng"] if meta else None,
        referencia=meta["referencia"] if meta else "",
        distancia_min=meta["distancia_min"] if meta else None,
    )


async def get_parking_product_adapter(
    db: AsyncSession,
    *,
    timestamp: datetime,
    event_id: str,
    user_context: UserContext,
    mobility_context: MobilityContext,
    limit: int = 5,
) -> ParkingRecommendationResponse:
    zone_type_map = await _load_zone_type_map(db)
    parking_zone_ids = await _load_parking_zone_ids(db, event_id, zone_type_map)

    if not parking_zone_ids:
        return ParkingRecommendationResponse(
            event_id=event_id,
            timestamp=timestamp.isoformat(),
            mode="sin_solucion",
            zonas=[],
        )

    requested_action = RequestedAction(action_type=ActionType.SEEK_PARKING)

    recs, prediction = await get_recommendations_adapter(
        db=db,
        timestamp=timestamp,
        event_id=event_id,
        user_context=user_context,
        mobility_context=mobility_context,
        requested_action=requested_action,
        limit=limit,
    )

    parking_recs = [r for r in recs if r.zone_id in parking_zone_ids]
    parking_recs = parking_recs[:limit]

    zone_meta = await _load_zone_metadata(db, [r.zone_id for r in parking_recs])

    zone_states_by_id: dict[UUID, ZoneState] = {}
    if prediction is not None:
        for zs in prediction.zone_states:
            zone_states_by_id[zs.zone_id] = zs

    enriched: list[ZonaEstacionamientoItem] = []
    for rec in parking_recs:
        state = zone_states_by_id.get(rec.zone_id)
        meta = zone_meta.get(rec.zone_id)
        enriched.append(_enrich_zone(rec, state, meta))

    mode = _compute_mode(enriched)

    return ParkingRecommendationResponse(
        event_id=event_id,
        timestamp=prediction.timestamp.isoformat()
        if prediction is not None
        else timestamp.isoformat(),
        mode=mode,
        zonas=enriched,
    )


async def _load_zone_type_map(db: AsyncSession) -> dict[str, UUID]:
    stmt = select(ZoneTypeORM)
    rows = (await db.execute(stmt)).scalars().all()
    return {r.slug: UUID(r.id) for r in rows}


async def _load_parking_zone_ids(
    db: AsyncSession,
    event_id: str,
    type_map: dict[str, UUID],
) -> set[UUID]:
    parking_type_id = type_map.get("parking")
    if parking_type_id is None:
        return set()

    stmt = select(ZoneORM).where(
        ZoneORM.event_id == event_id,
        ZoneORM.type == "parking",
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {UUID(r.id) for r in rows}


async def _load_zone_metadata(
    db: AsyncSession,
    zone_ids: list[UUID],
) -> dict[UUID, dict]:
    if not zone_ids:
        return {}

    id_strs = [str(zid) for zid in zone_ids]
    stmt = select(ZoneORM).where(ZoneORM.id.in_(id_strs))
    rows = (await db.execute(stmt)).scalars().all()

    result: dict[UUID, dict] = {}
    for r in rows:
        uid = UUID(r.id)
        result[uid] = {
            "name": r.name,
            "lat": r.latitude,
            "lng": r.longitude,
            "referencia": r.calle or r.name or "",
            "distancia_min": r.disponibilidad or r.espera_min or 5,
        }
    return result
