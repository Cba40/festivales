from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID

from src.application.context_engine.dto import (
    EventEvaluationResult,
    ZoneApplication,
    ZoneBehaviorApplicationResult,
)
from src.application.context_engine.exceptions import BehaviorNotDefined
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction, ZoneBehavior


def apply_zone_behaviors(
    zones: Sequence[Zone],
    zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
    attendance_level: AttendanceLevel,
    evaluation_result: EventEvaluationResult,
) -> ZoneBehaviorApplicationResult:
    zone_applications: dict[UUID, ZoneApplication] = {}

    active_phase = evaluation_result.active_operational_phase

    for zone in zones:
        behavior_key = (zone.zone_type_id, active_phase.id)
        behavior = zone_behaviors.get(behavior_key)

        if behavior is None:
            raise BehaviorNotDefined(zone.zone_type_id, active_phase.id)

        accumulated_impact = evaluation_result.event_impacts.get(zone.id, 0)

        projected_density = round(
            zone.capacity * attendance_level.multiplier * behavior.density_factor
        )
        projected_density += accumulated_impact

        if projected_density < 0:
            projected_density = 0

        active_restriction = behavior.flow_restriction
        if accumulated_impact <= -100:
            active_restriction = FlowRestriction.CLOSED

        zone_applications[zone.id] = ZoneApplication(
            zone_id=zone.id,
            projected_density=projected_density,
            active_restriction=active_restriction,
        )

    return ZoneBehaviorApplicationResult(
        active_operational_phase=active_phase,
        active_event_day_phase=evaluation_result.active_event_day_phase,
        timestamp=evaluation_result.timestamp,
        zone_applications=zone_applications,
    )
