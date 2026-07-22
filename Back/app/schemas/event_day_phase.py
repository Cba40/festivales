from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventDayPhaseCreate(BaseModel):
    operational_phase_id: UUID
    start_min: int = Field(ge=0)
    end_min: int = Field(ge=0)

    @model_validator(mode='after')
    def check_end_min(self) -> 'EventDayPhaseCreate':
        if self.end_min <= self.start_min:
            raise ValueError('end_min must be greater than start_min')
        return self


class EventDayPhaseUpdate(BaseModel):
    operational_phase_id: Optional[UUID] = None
    start_min: Optional[int] = Field(default=None, ge=0)
    end_min: Optional[int] = None

    @model_validator(mode='after')
    def check_end_min(self) -> 'EventDayPhaseUpdate':
        if self.start_min is not None and self.end_min is not None:
            if self.end_min <= self.start_min:
                raise ValueError('end_min must be greater than start_min')
        return self


class EventDayPhaseResponse(BaseModel):
    id: UUID
    event_day_id: str
    operational_phase_id: UUID
    start_min: int
    end_min: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
