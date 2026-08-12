from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from src.application.context_engine.dto import (
    EventEvaluationResult,
    ZoneBehaviorApplicationResult,
)
from src.application.context_engine.stage4_config import Stage4Config, get_stage4_config
from src.domain.entities.operational_event import OperationalEvent
from src.domain.models.specialized_model import ModelSpecificResult
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.value_objects.zone_state import ZoneState


def derive_zone_states(
    zone_behavior_result: ZoneBehaviorApplicationResult,
    zones: Sequence[Zone],
    active_events: Sequence[OperationalEvent],
    evaluation_result: EventEvaluationResult,
    config: Stage4Config | None = None,
    model_results: Mapping[UUID, ModelSpecificResult] | None = None,
) -> list[ZoneState]:
    resolved_config = config if config is not None else get_stage4_config()
    resolved_model_results = (
        model_results if model_results is not None else {}
    )

    zones_by_id: dict[UUID, Zone] = {z.id: z for z in zones}

    events_by_zone: dict[UUID, list[OperationalEvent]] = {}
    for event in active_events:
        zid = event.target_zone_id
        if zid not in events_by_zone:
            events_by_zone[zid] = []
        events_by_zone[zid].append(event)

    zone_states: list[ZoneState] = []

    for zone_id, zone_app in zone_behavior_result.zone_applications.items():
        zone = zones_by_id.get(zone_id)
        capacity = zone.capacity if zone is not None else 0
        zone_type = zone.type if zone is not None else ""
        zone_subtipo = zone.subtipo if zone is not None else None

        projected_density = zone_app.projected_density
        active_restriction = zone_app.active_restriction

        model_result = resolved_model_results.get(zone_id)
        model_data = model_result.data if model_result is not None else None

        # El estado operativo se clasifica desde el contexto territorial común
        # (densidad proyectada, restricciones). El modelo especializado puede
        # precisarlo si lo produce como resultado específico.
        operational_state = _determine_operational_state(
            projected_density, capacity, active_restriction, resolved_config
        )
        if model_data is not None and "operational_state" in model_data:
            operational_state = model_data["operational_state"]

        # Atributos de estado específicos: solo existen cuando el modelo
        # especializado correspondiente los produce (ADR-004). El Context
        # Engine NO genera fallback universal de estos valores.
        saturation_level = (
            model_data.get("saturation_level") if model_data is not None else None
        )
        availability = (
            model_data.get("availability") if model_data is not None else None
        )
        estimated_wait = (
            model_data.get("estimated_wait") if model_data is not None else None
        )
        confidence = model_data.get("confidence") if model_data is not None else None

        zone_events = events_by_zone.get(zone_id, [])
        accumulated_impact = evaluation_result.event_impacts.get(zone_id, 0)
        reasoning_factors = _build_reasoning_factors(
            accumulated_impact,
            zone_events,
            projected_density,
            capacity,
            active_restriction,
            resolved_config,
        )

        zone_states.append(
            ZoneState(
                zone_id=zone_id,
                operational_state=operational_state,
                availability=availability,
                saturation_level=saturation_level,
                estimated_wait=estimated_wait,
                confidence=confidence,
                reasoning_factors=reasoning_factors,
                active_restriction=active_restriction,
                type=zone_type,
                subtipo=zone_subtipo,
                projected_density=projected_density,
                model_result=model_data,
            )
        )

    return zone_states


def _density_ratio(projected_density: int, capacity: int) -> float:
    if capacity <= 0:
        return 0.0
    ratio = projected_density / capacity
    if ratio < 0.0:
        return 0.0
    if ratio > 1.0:
        return 1.0
    return ratio


def _determine_operational_state(
    projected_density: int,
    capacity: int,
    active_restriction: FlowRestriction,
    config: Stage4Config,
) -> str:
    if active_restriction == FlowRestriction.CLOSED:
        return "CLOSED"
    if active_restriction == FlowRestriction.REGULATED:
        return "REGULATED"
    ratio = _density_ratio(projected_density, capacity)
    if ratio >= config.saturation_high_threshold:
        return "HIGH_DEMAND"
    if ratio >= config.saturation_moderate_threshold:
        return "MODERATE"
    return "LOW_DEMAND"


def _build_reasoning_factors(
    accumulated_impact: int,
    zone_events: Sequence[OperationalEvent],
    projected_density: int,
    capacity: int,
    active_restriction: FlowRestriction,
    config: Stage4Config,
) -> list[str]:
    factors: list[str] = []

    if accumulated_impact != 0:
        factors.append(f"Impacto de evento operativo: {accumulated_impact}")

    if any(e.is_incident for e in zone_events):
        factors.append("Incidente activo en zona")

    if _density_ratio(projected_density, capacity) >= config.saturation_high_threshold:
        factors.append("Alta densidad proyectada")

    if active_restriction == FlowRestriction.REGULATED:
        factors.append("Acceso regulado")

    if active_restriction == FlowRestriction.CLOSED:
        factors.append("Zona cerrada")

    return factors