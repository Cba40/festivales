from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class OperationalObservationCreate(BaseModel):
    event_day_id: str = Field(..., description="ID del event day")
    zone_id: str = Field(..., description="ID de la zona")
    timestamp: datetime = Field(..., description="Timestamp timezone-aware")
    observed_density: int = Field(..., ge=0, description="Densidad observada (>= 0)")
    observer_id: Optional[str] = Field(default=None, description="ID del observador")
    source: str = Field(default="manual", description="Fuente: manual, sensor, official_report")
    metadata: Optional[dict] = Field(default=None, description="Metadatos adicionales")

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


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