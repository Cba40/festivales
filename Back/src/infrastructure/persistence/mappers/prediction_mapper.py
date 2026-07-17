from __future__ import annotations

from uuid import UUID

from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.infrastructure.persistence.models.prediction import PredictionModel


def _zone_state_to_dict(state: ZoneState) -> dict:
    return {
        "zone_id": str(state.zone_id),
        "operational_state": state.operational_state,
        "availability": state.availability,
        "saturation_level": state.saturation_level,
        "estimated_wait": state.estimated_wait,
        "confidence": state.confidence,
        "reasoning_factors": list(state.reasoning_factors),
        "active_restriction": state.active_restriction.value,
    }


def _zone_state_from_dict(data: dict) -> ZoneState:
    return ZoneState(
        zone_id=UUID(data["zone_id"]),
        operational_state=data["operational_state"],
        availability=data["availability"],
        saturation_level=data["saturation_level"],
        estimated_wait=data["estimated_wait"],
        confidence=data["confidence"],
        reasoning_factors=list(data["reasoning_factors"]),
        active_restriction=FlowRestriction(data["active_restriction"]),
    )


def prediction_to_domain(model: PredictionModel) -> TerritorialPrediction:
    zone_states = [_zone_state_from_dict(item) for item in model.zone_states_data]
    return TerritorialPrediction(
        timestamp=model.timestamp,
        zone_states=zone_states,
        active_phase_id=model.active_phase_id,
        active_event_day_phase_id=model.active_event_day_phase_id,
    )


def prediction_to_model(entity: TerritorialPrediction) -> PredictionModel:
    return PredictionModel(
        timestamp=entity.timestamp,
        active_phase_id=entity.active_phase_id,
        active_event_day_phase_id=entity.active_event_day_phase_id,
        zone_states_data=[
            _zone_state_to_dict(state) for state in entity.zone_states
        ],
    )
