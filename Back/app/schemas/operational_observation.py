from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class OperationalObservationCreate(BaseModel):
    event_day_id: str = Field(..., description="ID del event day")
    zone_id: str = Field(..., description="ID de la zona")
    observed_density: int = Field(..., ge=0, description="Densidad observada")
    observer_id: Optional[str] = Field(default=None, description="ID del observador")
    source: str = Field(default="manual", description="Fuente de la observación")
    metadata: Optional[dict] = Field(default=None, description="Metadatos adicionales")


class OperationalObservationResponse(BaseModel):
    id: str = Field(..., description="ID de la observación")
    event_day_id: str = Field(..., description="ID del event day")
    zone_id: str = Field(..., description="ID de la zona")
    timestamp: datetime = Field(..., description="Timestamp de la observación")
    observed_density: int = Field(..., ge=0, description="Densidad observada")
    observer_id: Optional[str] = Field(default=None, description="ID del observador")
    source: str = Field(default="manual", description="Fuente de la observación")
    metadata: Optional[dict] = Field(default=None, description="Metadatos adicionales")
    created_at: datetime = Field(..., description="Fecha de creación")

    model_config = ConfigDict(from_attributes=True)