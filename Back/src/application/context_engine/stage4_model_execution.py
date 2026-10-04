"""Etapa 4 (modelos especializados): selección y ejecución de modelos.

Tras resolver el contexto territorial común (Etapas 1-3), el Context Engine
selecciona, para cada Zone, el modelo especializado correspondiente mediante
un selector determinista y lo ejecuta entregándole el contexto resuelto.
Esta etapa NO contiene fórmulas de ningún modelo: solo conoce el contrato.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from uuid import UUID

from src.application.context_engine.dto import (
    EventEvaluationResult,
    ZoneApplication,
    ZoneBehaviorApplicationResult,
)
from src.application.context_engine.model_selector import ModelSelector
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.event_day import EventDay
from src.domain.entities.zone import Zone
from src.domain.models.specialized_model import (
    ModelExecutionContext,
    ModelSpecificResult,
)

logger = logging.getLogger(__name__)


def _build_execution_context(
    zone: Zone,
    zone_app: ZoneApplication,
    evaluation_result: EventEvaluationResult,
    attendance_level: AttendanceLevel | None,
    event_day: EventDay,
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
        estimated_vehicles=event_day.estimated_vehicles,
        average_parking_duration=event_day.average_parking_duration,
    )


def execute_specialized_models(
    zone_behavior_result: ZoneBehaviorApplicationResult,
    zones: Sequence[Zone],
    evaluation_result: EventEvaluationResult,
    attendance_level: AttendanceLevel | None,
    event_day: EventDay,
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
            event_day,
        )
        # Aislamiento por zona. Un modelo especializado puede legitimately no
        # poder calcular: ParkingV1 exige `event_days.estimated_vehicles` y
        # BathroomV1 exige `attendance_level.max_people`, y los dos son
        # NULLABLE en la base. Sin este try, UN parking sin
        # `estimated_vehicles` levanta ValueError y tumba el endpoint público
        # `/predictions` completo con un 500, perdiendo las 39 zonashealthy
        # junto con la que no se pudo calcular.
        #
        # Se degrada a "sin resultado de modelo": la zona sigue saliendo con el
        # contexto territorial comun (`derive_zone_states` la resuelve con el
        # fallback de `_determine_operational_state`), solo que sin
        # `saturation_level` / `availability` / `estimated_wait` / `confidence`.
        # Un endpoint público no puede caerse por datos faltantes de UNA zona.
        #
        # Se loguea en warning con la excepción, no se traga en silencio: un
        # modelo que empieza a fallar en todos lados tiene que verse.
        try:
            results[zone.id] = model.execute(context)
        except Exception:
            logger.warning(
                "El modelo especializado %s no pudo calcular la zona %s "
                "(type=%r, subtipo=%r); se degrada al contexto territorial común "
                "sin saturación/availability/espera/confianza. "
                "Revisar estimated_vehicles del EventDay y "
                "attendance_level.max_people.",
                getattr(model, "model_id", model.__class__.__name__),
                zone.id,
                zone.type,
                zone.subtipo,
                exc_info=True,
            )

    return results