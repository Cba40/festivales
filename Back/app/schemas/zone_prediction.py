from typing import Optional

from pydantic import BaseModel

from app.schemas.event_state import EventStateResponse
from app.schemas.state_override import StateOverrideResponse


class ZonePrediction(BaseModel):
    id: str
    name: str
    type: str
    factores: dict
    prediccion: dict


class CurrentStateResponse(BaseModel):
    estado_actual: Optional[EventStateResponse] = None
    override_activo: Optional[StateOverrideResponse] = None


class ContextEngineResponse(BaseModel):
    estado_actual: Optional[EventStateResponse] = None
    override_activo: Optional[StateOverrideResponse] = None
    zonas: list[ZonePrediction]
