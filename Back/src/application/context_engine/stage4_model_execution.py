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
    MissingModelInputError,
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
    service_durations: Mapping[UUID, float] | None = None,
) -> ModelExecutionContext:
    """Arma el contexto común que consume el modelo especializado.

    `service_durations` es el mapa `zone_id -> average_duration_min` (MINUTOS)
    que la capa de composición ya resolvió desde `service_configs`: esta etapa
    es síncrona y no tiene sesión de base, así que la duración de permanencia
    de un servicio tiene que llegar resuelta desde afuera. Sin entrada para la
    zona, `average_duration_min` queda en `None` y el modelo que lo exige
    degrada (no revienta): ver el aislamiento por zona de abajo.
    """
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
        average_duration_min=(service_durations or {}).get(zone.id),
    )


def execute_specialized_models(
    zone_behavior_result: ZoneBehaviorApplicationResult,
    zones: Sequence[Zone],
    evaluation_result: EventEvaluationResult,
    attendance_level: AttendanceLevel | None,
    event_day: EventDay,
    model_selector: ModelSelector | None = None,
    service_durations: Mapping[UUID, float] | None = None,
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
            service_durations,
        )
        # Aislamiento por zona. Un modelo especializado puede legitimately no
        # poder calcular: ParkingV1 exige `event_days.estimated_vehicles` y
        # BathroomV1 exige `attendance_level.max_people`, y los dos son
        # NULLABLE en la base. Sin este try, UN parking sin
        # `estimated_vehicles` levanta ValueError y tumba el endpoint público
        # `/predictions` completo con un 500, perdiendo las 39 zonashealthy
        # junto con la que no se pudo calcular.
        #
        # Lo mismo pasa con los datos que llegan YA resueltos desde afuera y
        # siguen siendo opcionales: si `service_configs` no tiene fila para
        # `average_duration_min` (bathrooms incluidos), esa zona degrada por la
        # misma vía y las otras 38 no se enteran.
        #
        # Se degrada a "sin resultado de modelo": la zona sigue saliendo con el
        # contexto territorial comun (`derive_zone_states` la resuelve con el
        # fallback de `_determine_operational_state`), solo que sin
        # `saturation_level` / `availability` / `estimated_wait` / `confidence`.
        # Un endpoint público no puede caerse por datos faltantes de UNA zona.
        #
        # Dos niveles de log según la causa. Un hueco de datos conocido
        # (`MissingModelInputError`: sin fila en `service_configs`, sin
        # `attendance_level.max_people`) degrada en silencio a propósito: 9
        # baños sin configurar serían 9 tracebacks por pedido a `/predictions`
        # y ahogarían los fallos de verdad. Cualquier otra excepción sí es un
        # fallo que hay que mirar, y va con warning + traceback una vez por zona.
        try:
            results[zone.id] = model.execute(context)
        except MissingModelInputError as exc:
            logger.info(
                "El modelo especializado %s no calculó la zona %s "
                "(type=%r, subtipo=%r) por falta de datos: %s. "
                "Se degrada al contexto territorial común sin saturación.",
                getattr(model, "model_id", model.__class__.__name__),
                zone.id,
                zone.type,
                zone.subtipo,
                exc,
            )
        except Exception:
            logger.warning(
                "El modelo especializado %s no pudo calcular la zona %s "
                "(type=%r, subtipo=%r); se degrada al contexto territorial común "
                "sin saturación/availability/espera/confianza. "
                "Revisar estimated_vehicles del EventDay, "
                "attendance_level.max_people y service_configs."
                "average_duration_min.",
                getattr(model, "model_id", model.__class__.__name__),
                zone.id,
                zone.type,
                zone.subtipo,
                exc_info=True,
            )

    return results