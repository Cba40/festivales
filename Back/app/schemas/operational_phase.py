"""OperationalPhase: Contexto operativo del territorio."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OperationalPhaseCreate(BaseModel):
    """Schema para crear una nueva fase operativa."""
    operational_profile_id: UUID
    name: str = Field(min_length=1, max_length=100)
    sort_order: int = Field(ge=0)


class OperationalPhaseUpdate(BaseModel):
    """Schema para actualizar una fase operativa existente."""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    sort_order: int | None = Field(default=None, ge=0)


class OperationalPhaseResponse(BaseModel):
    """Representacion de una fase operativa."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    operational_profile_id: UUID
    name: str
    sort_order: int
    created_at: datetime
    updated_at: datetime
