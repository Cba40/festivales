from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.zone import Zone as ZoneORM
from app.schemas.product import ZonaItemBase
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.zone_state import ZoneState


def saturation_to_estado(saturation_level: float) -> str:
    if saturation_level < 0.25:
        return "bajo"
    if saturation_level < 0.50:
        return "medio"
    if saturation_level < 0.75:
        return "alto"
    return "colapsado"


def compute_mode(
    estados: list[str],
) -> str:
    if not estados:
        return "sin_solucion"

    colapsadas = [e for e in estados if e == "colapsado"]
    saturadas = [e for e in estados if e in ("alto", "colapsado")]

    if len(colapsadas) == len(estados):
        return "sin_solucion"
    if len(saturadas) == len(estados):
        return "guiar"
    if len(saturadas) > len(estados) / 2:
        return "asistir"
    return "informar"


async def load_zone_metadata(
    db: AsyncSession,
    zone_ids: list[UUID],
    extra_fields_fn=None,
) -> dict[UUID, dict]:
    if not zone_ids:
        return {}

    id_strs = [str(zid) for zid in zone_ids]
    stmt = select(ZoneORM).where(ZoneORM.id.in_(id_strs))
    rows = (await db.execute(stmt)).scalars().all()

    result: dict[UUID, dict] = {}
    for r in rows:
        uid = UUID(r.id)
        base = {
            "name": r.name,
            "lat": r.latitude,
            "lng": r.longitude,
            "referencia": r.calle or r.name or "",
            "distancia_min": r.disponibilidad or r.espera_min or 5,
        }
        if extra_fields_fn:
            base.update(extra_fields_fn(r))
        result[uid] = base
    return result


def enrich_zone(
    rec: ZoneRecommendation,
    state: ZoneState | None,
    meta: dict | None,
    dto_cls: type[ZonaItemBase],
    extra_fields: dict | None = None,
) -> ZonaItemBase:
    if state is not None:
        # Atributos de estado específicos: solo existen cuando el modelo
        # especializado los produce (ADR-004). Cuando no existen se preservan
        # como None; NO se sustituyen por valores sintéticos ni se infieren.
        saturation_level = state.saturation_level
        availability = state.availability
        estimated_wait = state.estimated_wait
        confidence = state.confidence
        active_restriction = (
            state.active_restriction.value
            if state.active_restriction is not None
            else "OPEN"
        )
        operational_state = state.operational_state
    else:
        saturation_level = None
        availability = None
        estimated_wait = None
        confidence = None
        active_restriction = "OPEN"
        operational_state = "UNKNOWN"

    estado = (
        saturation_to_estado(saturation_level)
        if saturation_level is not None
        else None
    )

    kwargs = dict(
        zone_id=str(rec.zone_id),
        name=meta["name"] if meta else str(rec.zone_id),
        score=rec.score,
        reasoning=list(rec.reasoning),
        saturation_level=saturation_level,
        estado=estado,
        availability=availability,
        estimated_wait=estimated_wait,
        confidence=confidence,
        active_restriction=active_restriction,
        operational_state=operational_state,
        lat=meta["lat"] if meta else None,
        lng=meta["lng"] if meta else None,
        referencia=meta["referencia"] if meta else "",
        distancia_min=meta["distancia_min"] if meta else None,
        is_nearest=rec.is_nearest,
    )
    if extra_fields:
        kwargs.update(extra_fields)
    return dto_cls(**kwargs)
