"""OperationalPhase: Contexto operativo del territorio."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OperationalPhaseCreate(BaseModel):
    """Schema para crear una nueva fase operativa."""
    operational_profile_id: UUID
    name: str = Field(min_length=1, max_length=100)
    start_min: int = Field(ge=0)
    end_min: int = Field(ge=0)
    sort_order: int = Field(ge=0)

    @model_validator(mode='after')
    def check_end_min(self) -> 'OperationalPhaseCreate':
        if self.end_min <= self.start_min:
            raise ValueError('end_min must be greater than start_min')
        return self


class OperationalPhaseUpdate(BaseModel):
    """Schema para actualizar una fase operativa existente."""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    start_min: int | None = Field(default=None, ge=0)
    end_min: int | None = Field(default=None)
    sort_order: int | None = Field(default=None, ge=0)

    @model_validator(mode='after')
    def check_end_min(self) -> 'OperationalPhaseUpdate':
        if self.start_min is not None and self.end_min is not None:
            if self.end_min <= self.start_min:
                raise ValueError('end_min must be greater than start_min')
        return self


class OperationalPhaseResponse(BaseModel):
    """Representacion de una fase operativa."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    operational_profile_id: UUID
    name: str
    start_min: int
    end_min: int
    sort_order: int
    created_at: datetime
    updated_at: datetime
