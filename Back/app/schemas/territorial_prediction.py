"""TerritorialPrediction: Salida del Context Engine."""
from datetime import datetime
from pydantic import BaseModel, Field


class ZonePrediction(BaseModel):
    """Prediccion del comportamiento esperado de una zona en un instante operativo."""
    zone_id: str
    zone_type: str
    saturation_predicted: float = Field(ge=0.0)
    attendance_predicted: float = Field(ge=0.0)
    resource_required: float = Field(ge=0.0)
    priority_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    recommendation: str | None = None


class TerritorialPrediction(BaseModel):
    """Resultado final del Context Engine.
    Representa la evaluacion contextual del comportamiento esperado
    de todos los servicios territoriales para un instante operativo.
    """
    zones: list[ZonePrediction]
    current_phase: str
    attendance_level: str
    active_events: list[str]
    timestamp: datetime
