"""Pydantic response DTOs for the predictions endpoint."""
from __future__ import annotations

from pydantic import BaseModel


class ZoneStateItem(BaseModel):
    zone_id: str
    operational_state: str
    availability: int
    saturation_level: float
    estimated_wait: int
    confidence: float
    reasoning_factors: list[str]
    active_restriction: str


class TerritorialPredictionResponse(BaseModel):
    timestamp: str
    active_phase_id: str
    active_event_day_phase_id: str
    zone_states: list[ZoneStateItem]
