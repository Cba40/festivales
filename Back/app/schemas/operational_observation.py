"""OperationalObservation: Registro de densidad observada en zona durante una jornada."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OperationalObservationCreate(BaseModel):
    """Schema para crear una nueva observación operativa."""
    event_day_id: UUID
    zone_id: UUID
    timestamp: datetime
    observed_density: int = Field(ge=0)
    observer_id: Optional[UUID] = None
    source: str = "manual"
    metadata: Optional[dict] = None


class OperationalObservationResponse(BaseModel):
    """Representación de una observación operativa."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_day_id: UUID
    zone_id: UUID
    timestamp: datetime
    observed_density: int
    observer_id: Optional[UUID]
    source: str
    metadata: Optional[dict]
    created_at: datetime