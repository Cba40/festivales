from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator


class EventDayCreate(BaseModel):
    date: date
    day_of_week: str
    weather: Optional[str] = None
    headliner_artist: Optional[str] = None
    expected_attendance: Optional[int] = None
    peak_hour_start: Optional[int] = None
    peak_hour_end: Optional[int] = None
    opening_time: Optional[int] = None
    closing_time: Optional[int] = None
    notes: Optional[str] = None
    is_active: bool = True


class EventDayUpdate(BaseModel):
    date: Optional[date] = None
    day_of_week: Optional[str] = None
    weather: Optional[str] = None
    headliner_artist: Optional[str] = None
    expected_attendance: Optional[int] = None
    peak_hour_start: Optional[int] = None
    peak_hour_end: Optional[int] = None
    opening_time: Optional[int] = None
    closing_time: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class EventDayResponse(BaseModel):
    id: str
    event_id: str
    date: date
    day_of_week: str
    weather: Optional[str]
    headliner_artist: Optional[str]
    expected_attendance: Optional[int]
    peak_hour_start: Optional[int]
    peak_hour_end: Optional[int]
    opening_time: Optional[int]
    closing_time: Optional[int]
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
    weather: Optional[str]
    headliner_artist: Optional[str]
    expected_attendance: Optional[int]
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
