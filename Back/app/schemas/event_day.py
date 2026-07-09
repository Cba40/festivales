from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator


class EventDayCreate(BaseModel):
    date: date
    day_of_week: str
    entry_start_min: int
    activity_peak_start_min: int
    activity_peak_end_min: int
    exit_start_min: int
    event_end_min: int
    weather: Optional[str] = None
    headliner_artist: Optional[str] = None
    estimated_attendance: int = 0
    notes: Optional[str] = None
    is_active: bool = True


class EventDayUpdate(BaseModel):
    date: Optional[date] = None
    day_of_week: Optional[str] = None
    entry_start_min: Optional[int] = None
    activity_peak_start_min: Optional[int] = None
    activity_peak_end_min: Optional[int] = None
    exit_start_min: Optional[int] = None
    event_end_min: Optional[int] = None
    weather: Optional[str] = None
    headliner_artist: Optional[str] = None
    estimated_attendance: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class EventDayResponse(BaseModel):
    id: str
    event_id: str
    date: date
    day_of_week: str
    entry_start_min: int
    activity_peak_start_min: int
    activity_peak_end_min: int
    exit_start_min: int
    event_end_min: int
    weather: Optional[str]
    headliner_artist: Optional[str]
    estimated_attendance: int
    notes: Optional[str]
    is_active: bool
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
    entry_start_min: int
    activity_peak_start_min: int
    activity_peak_end_min: int
    exit_start_min: int
    event_end_min: int
    weather: Optional[str]
    headliner_artist: Optional[str]
    estimated_attendance: int
    is_active: bool

    @field_validator("date", mode="before")
    @classmethod
    def coerce_date(cls, value):
        if isinstance(value, datetime):
            return value.date()
        return value

    @field_serializer("date")
    def serialize_date(self, value: date) -> str:
        return value.isoformat()
