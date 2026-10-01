from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.infrastructure.persistence.models.prediction import PredictionModel


def prediction_timestamp_to_storage(value: datetime) -> datetime:
    """Normaliza un instante a la convencion de almacenamiento de `predictions`.

    `predictions.timestamp` es `timestamp without time zone`, y el valor que
    fluye por el dominio es la hora local de la jornada (`astimezone(LOCAL_TZ)`
    en `prediction_module.py`), no UTC. Guardar esa hora local sin declararlo
    dejaba la columna ambigua y rompia a todo consumidor que la compara con un
    instante UTC:

      - `MetricService._as_utc` interpreta los naive como UTC, asi que la
        desviacion media nunca caia en la ventana de ±30 min y
        `density_deviation` quedaba BLOCKED de forma permanente.
      - `app/crud/operational_event.py` compara la columna contra
        `start_timestamp`/`end_timestamp`, que si son UTC (RFC-OPERATIONAL-EVENTS-V1),
        con el mismo desfase de 3 h.

    Se elige UTC como convencion unica porque es la que ya asumian los dos
    lectores. Se hace aqui, en la frontera de persistencia, y no en el motor:
    la entidad de dominio conserva su instante local con timezone, asi que los
    endpoints que exponen `prediction.timestamp.isoformat()` no cambian.

    Una columna `timestamp without time zone` guarda el literal tal cual, sin
    convertir por el `TimeZone` de la sesion, asi que el resultado no depende de
    como este configurado Postgres.
    """
    if value.tzinfo is None:
        # Sin timezone no hay nada que convertir: se asume que ya es UTC, que es
        # lo que historicamente guardaba esta columna.
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _zone_state_to_dict(state: ZoneState) -> dict:
    model_result = (
        dict(state.model_result) if state.model_result is not None else None
    )
    return {
        "zone_id": str(state.zone_id),
        "operational_state": state.operational_state,
        "availability": state.availability,
        "saturation_level": state.saturation_level,
        "estimated_wait": state.estimated_wait,
        "confidence": state.confidence,
        "reasoning_factors": list(state.reasoning_factors),
        "active_restriction": (
            state.active_restriction.value
            if state.active_restriction is not None
            else None
        ),
        "type": state.type,
        "subtipo": state.subtipo,
        "projected_density": state.projected_density,
        "model_result": model_result,
    }


def _zone_state_from_dict(data: dict) -> ZoneState:
    active_restriction = data.get("active_restriction")
    return ZoneState(
        zone_id=UUID(data["zone_id"]),
        operational_state=data["operational_state"],
        availability=data.get("availability"),
        saturation_level=data.get("saturation_level"),
        estimated_wait=data.get("estimated_wait"),
        confidence=data.get("confidence"),
        reasoning_factors=list(data.get("reasoning_factors") or []),
        active_restriction=(
            FlowRestriction(active_restriction)
            if active_restriction is not None
            else None
        ),
        type=data.get("type", ""),
        subtipo=data.get("subtipo"),
        projected_density=data.get("projected_density", 0),
        model_result=data.get("model_result"),
    )


def prediction_to_domain(model: PredictionModel) -> TerritorialPrediction:
    zone_states = [_zone_state_from_dict(item) for item in model.zone_states_data]
    return TerritorialPrediction(
        timestamp=model.timestamp,
        zone_states=zone_states,
        active_phase_id=model.active_phase_id,
        active_event_day_phase_id=model.active_event_day_phase_id,
        event_day_id=str(model.event_day_id) if model.event_day_id else None,
        knowledge_model_version_id=model.knowledge_model_version_id,
    )


def prediction_to_model(entity: TerritorialPrediction) -> PredictionModel:
    return PredictionModel(
        timestamp=prediction_timestamp_to_storage(entity.timestamp),
        event_day_id=entity.event_day_id,
        knowledge_model_version_id=entity.knowledge_model_version_id,
        active_phase_id=entity.active_phase_id,
        active_event_day_phase_id=entity.active_event_day_phase_id,
        zone_states_data=[
            _zone_state_to_dict(state) for state in entity.zone_states
        ],
    )
