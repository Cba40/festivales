from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from src.application.context_engine.dto import (
    EventEvaluationResult,
    ZoneBehaviorApplicationResult,
)
from src.application.context_engine.stage4_config import Stage4Config, get_stage4_config
from src.domain.entities.operational_event import OperationalEvent
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.value_objects.zone_state import ZoneState


def derive_zone_states(
    zone_behavior_result: ZoneBehaviorApplicationResult,
    zones: Sequence[Zone],
    active_events: Sequence[OperationalEvent],
    evaluation_result: EventEvaluationResult,
    config: Stage4Config | None = None,
) -> list[ZoneState]:
    resolved_config = config if config is not None else get_stage4_config()

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

        projected_density = zone_app.projected_density
        active_restriction = zone_app.active_restriction

        saturation_level = _compute_saturation_level(projected_density, capacity)
        availability = _compute_availability(capacity, projected_density)
        operational_state = _determine_operational_state(
            saturation_level, active_restriction, resolved_config
        )
        estimated_wait = _estimate_wait(saturation_level, resolved_config)

        zone_events = events_by_zone.get(zone_id, [])
        accumulated_impact = evaluation_result.event_impacts.get(zone_id, 0)
        confidence = _compute_confidence(zone_events, resolved_config)
        reasoning_factors = _build_reasoning_factors(
            accumulated_impact, zone_events, saturation_level, active_restriction
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
            )
        )

    return zone_states


def _compute_saturation_level(projected_density: int, capacity: int) -> float:
    if capacity <= 0:
        return 0.0
    raw = projected_density / capacity
    if raw < 0.0:
        return 0.0
    if raw > 1.0:
        return 1.0
    return raw


def _compute_availability(capacity: int, projected_density: int) -> int:
    remaining = capacity - projected_density
    return remaining if remaining > 0 else 0


def _determine_operational_state(
    saturation_level: float,
    active_restriction: FlowRestriction,
    config: Stage4Config,
) -> str:
    if active_restriction == FlowRestriction.CLOSED:
        return "CLOSED"
    if active_restriction == FlowRestriction.REGULATED:
        return "REGULATED"
    if saturation_level >= config.saturation_high_threshold:
        return "HIGH_DEMAND"
    if saturation_level >= config.saturation_moderate_threshold:
        return "MODERATE"
    return "LOW_DEMAND"


def _estimate_wait(saturation_level: float, config: Stage4Config) -> int:
    for low, high, wait in config.wait_time_mapping:
        if low <= saturation_level < high:
            return wait
    if saturation_level >= 1.0 and config.wait_time_mapping:
        _, _, last_wait = config.wait_time_mapping[-1]
        return last_wait
    return 0


def _compute_confidence(
    zone_events: Sequence[OperationalEvent],
    config: Stage4Config,
) -> float:
    has_incident = any(e.is_incident for e in zone_events)
    if has_incident:
        return config.confidence_incident
    if zone_events:
        return config.confidence_planned_events
    return config.confidence_no_events


def _build_reasoning_factors(
    accumulated_impact: int,
    zone_events: Sequence[OperationalEvent],
    saturation_level: float,
    active_restriction: FlowRestriction,
) -> list[str]:
    factors: list[str] = []

    if accumulated_impact != 0:
        factors.append(f"Impacto de evento operativo: {accumulated_impact}")

    if any(e.is_incident for e in zone_events):
        factors.append("Incidente activo en zona")

    if saturation_level >= 0.9:
        factors.append("Alta saturación proyectada")

    if active_restriction == FlowRestriction.REGULATED:
        factors.append("Acceso regulado")

    if active_restriction == FlowRestriction.CLOSED:
        factors.append("Zona cerrada")

    return factors
