"""OperationalEvent: Hechos reales ocurridos durante una jornada."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

EVENT_TYPE_LITERAL = Literal[
    "fin_espectaculo",
    "tormenta",
    "evacuacion",
    "corte_energia",
    "incidente_operativo",
]


class OperationalEventCreate(BaseModel):
    """Schema para crear un nuevo evento operativo."""
    event_day_id: str = Field(max_length=36)
    event_type: EVENT_TYPE_LITERAL
    start_min: int = Field(ge=0)
    end_min: int | None = Field(default=None)
    is_active: bool = True

    @model_validator(mode='after')
    def check_end_min(self) -> 'OperationalEventCreate':
        if self.end_min is not None and self.end_min <= self.start_min:
            raise ValueError('end_min must be greater than start_min')
        return self


class OperationalEventUpdate(BaseModel):
    """Schema para actualizar un evento operativo existente."""
    event_type: EVENT_TYPE_LITERAL | None = Field(default=None)
    start_min: int | None = Field(default=None, ge=0)
    end_min: int | None = Field(default=None)
    is_active: bool | None = Field(default=None)

    @model_validator(mode='after')
    def check_end_min(self) -> 'OperationalEventUpdate':
        if self.start_min is not None and self.end_min is not None:
            if self.end_min <= self.start_min:
                raise ValueError('end_min must be greater than start_min')
        return self


class OperationalEventResponse(BaseModel):
    """Representacion de un evento operativo."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_day_id: str
    event_type: str
    start_min: int
    end_min: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
