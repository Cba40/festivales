from __future__ import annotations

from uuid import UUID

from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.infrastructure.persistence.models.prediction import PredictionModel


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
        event_day_id=model.event_day_id,
        knowledge_model_version_id=model.knowledge_model_version_id,
    )


def prediction_to_model(entity: TerritorialPrediction) -> PredictionModel:
    return PredictionModel(
        timestamp=entity.timestamp,
        event_day_id=entity.event_day_id,
        knowledge_model_version_id=entity.knowledge_model_version_id,
        active_phase_id=entity.active_phase_id,
        active_event_day_phase_id=entity.active_event_day_phase_id,
        zone_states_data=[
            _zone_state_to_dict(state) for state in entity.zone_states
        ],
    )
