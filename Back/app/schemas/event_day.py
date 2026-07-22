from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, model_validator

from app.schemas.event_day_phase import EventDayPhaseCreate, EventDayPhaseResponse


class EventDayCreate(BaseModel):
    date: date
    day_of_week: str
    weather: Optional[str] = None
    headliner_artist: Optional[str] = None
    estimated_attendance: int = 0
    notes: Optional[str] = None
    is_active: bool = True
    operational_profile_id: UUID
    attendance_level_id: str
    operational_start_min: int = Field(ge=0)
    operational_end_min: int = Field(ge=0)
    phases: list[EventDayPhaseCreate] = []

    @model_validator(mode='after')
    def check_operational_end(self) -> 'EventDayCreate':
        if self.operational_end_min <= self.operational_start_min:
            raise ValueError('operational_end_min must be greater than operational_start_min')
        return self


class EventDayUpdate(BaseModel):
    date: Optional[date] = None
    day_of_week: Optional[str] = None
    weather: Optional[str] = None
    headliner_artist: Optional[str] = None
    estimated_attendance: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    operational_profile_id: Optional[UUID] = None
    attendance_level_id: Optional[str] = None
    operational_start_min: Optional[int] = Field(default=None, ge=0)
    operational_end_min: Optional[int] = None
    phases: Optional[list[EventDayPhaseCreate]] = None

    @model_validator(mode='after')
    def check_operational_end(self) -> 'EventDayUpdate':
        if self.operational_start_min is not None and self.operational_end_min is not None:
            if self.operational_end_min <= self.operational_start_min:
                raise ValueError('operational_end_min must be greater than operational_start_min')
        return self


class EventDayResponse(BaseModel):
    id: str
    event_id: str
    date: date
    day_of_week: str
    weather: Optional[str]
    headliner_artist: Optional[str]
    estimated_attendance: int
    notes: Optional[str]
    is_active: bool
    operational_profile_id: UUID
    attendance_level_id: str
    operational_start_min: int
    operational_end_min: int
    phases: list[EventDayPhaseResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("date", mode="before")
    @classmethod
    def coerce_date(cls, value):
        if isinstance(value, datetime):
            return value.date()
        return value

    @field_serializer("date")
    def serialize_date(self, value: date) -> str:
        return value.isoformat()


class EventDaySummary(BaseModel):
    id: str
    date: date
    day_of_week: str
    weather: Optional[str]
    headliner_artist: Optional[str]
    estimated_attendance: int
    is_active: bool
    operational_profile_id: UUID
    attendance_level_id: str
    operational_start_min: int
    operational_end_min: int

    @field_validator("date", mode="before")
    @classmethod
    def coerce_date(cls, value):
        if isinstance(value, datetime):
            return value.date()
        return value

    @field_serializer("date")
    def serialize_date(self, value: date) -> str:
        return value.isoformat()
