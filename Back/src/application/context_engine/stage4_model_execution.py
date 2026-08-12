"""Etapa 4 (modelos especializados): selección y ejecución de modelos.

Tras resolver el contexto territorial común (Etapas 1-3), el Context Engine
selecciona, para cada Zone, el modelo especializado correspondiente mediante
un selector determinista y lo ejecuta entregándole el contexto resuelto.
Esta etapa NO contiene fórmulas de ningún modelo: solo conoce el contrato.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from src.application.context_engine.dto import (
    EventEvaluationResult,
    ZoneApplication,
    ZoneBehaviorApplicationResult,
)
from src.application.context_engine.model_selector import ModelSelector
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.zone import Zone
from src.domain.models.specialized_model import (
    ModelExecutionContext,
    ModelSpecificResult,
)


def _build_execution_context(
    zone: Zone,
    zone_app: ZoneApplication,
    evaluation_result: EventEvaluationResult,
    attendance_level: AttendanceLevel | None,
) -> ModelExecutionContext:
    day_phase = evaluation_result.active_event_day_phase
    return ModelExecutionContext(
        timestamp=evaluation_result.timestamp,
        zone=zone,
        active_operational_phase=evaluation_result.active_operational_phase,
        active_event_day_phase=day_phase,
        intensity=day_phase.intensity,
        attendance_level=attendance_level,
        event_impact=evaluation_result.event_impacts.get(zone.id, 0),
        density_factor=zone_app.density_factor,
        active_restriction=zone_app.active_restriction,
        reference_point_distance=zone.reference_point_distance,
    )


def execute_specialized_models(
    zone_behavior_result: ZoneBehaviorApplicationResult,
    zones: Sequence[Zone],
    evaluation_result: EventEvaluationResult,
    attendance_level: AttendanceLevel | None,
    model_selector: ModelSelector | None = None,
) -> Mapping[UUID, ModelSpecificResult]:
    if model_selector is None:
        return {}

    zone_apps = zone_behavior_result.zone_applications
    results: dict[UUID, ModelSpecificResult] = {}

    for zone in zones:
        zone_app = zone_apps.get(zone.id)
        if zone_app is None:
            continue
        model = model_selector.select(zone)
        if model is None:
            continue
        context = _build_execution_context(
            zone,
            zone_app,
            evaluation_result,
            attendance_level,
        )
        results[zone.id] = model.execute(context)

    return results