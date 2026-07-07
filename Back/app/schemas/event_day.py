from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator


class EventDayCreate(BaseModel):
    date: date
    day_of_week: str
    entry_start_time: time
    entry_peak_start_time: time
    entry_peak_end_time: time
    event_start_time: time
    exit_peak_start_time: time
    exit_peak_end_time: time
    event_end_time: time
    weather: Optional[str] = None
    headliner_artist: Optional[str] = None
    expected_attendance: Optional[int] = None
    notes: Optional[str] = None
    is_active: bool = True


class EventDayUpdate(BaseModel):
    date: Optional[date] = None
    day_of_week: Optional[str] = None
    entry_start_time: Optional[time] = None
    entry_peak_start_time: Optional[time] = None
    entry_peak_end_time: Optional[time] = None
    event_start_time: Optional[time] = None
    exit_peak_start_time: Optional[time] = None
    exit_peak_end_time: Optional[time] = None
    event_end_time: Optional[time] = None
    weather: Optional[str] = None
    headliner_artist: Optional[str] = None
    expected_attendance: Optional[int] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class EventDayResponse(BaseModel):
    id: str
    event_id: str
    date: date
    day_of_week: str
    entry_start_time: time
    entry_peak_start_time: time
    entry_peak_end_time: time
    event_start_time: time
    exit_peak_start_time: time
    exit_peak_end_time: time
    event_end_time: time
    weather: Optional[str]
    headliner_artist: Optional[str]
    expected_attendance: Optional[int]
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

    @field_serializer("entry_start_time", "entry_peak_start_time", "entry_peak_end_time", "event_start_time", "exit_peak_start_time", "exit_peak_end_time", "event_end_time")
    def serialize_time(self, value: time) -> str:
        return value.strftime("%H:%M")


class EventDaySummary(BaseModel):
    id: str
    date: date
    day_of_week: str
    entry_start_time: time
    entry_peak_start_time: time
    entry_peak_end_time: time
    event_start_time: time
    exit_peak_start_time: time
    exit_peak_end_time: time
    event_end_time: time
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

    @field_serializer("entry_start_time", "entry_peak_start_time", "entry_peak_end_time", "event_start_time", "exit_peak_start_time", "exit_peak_end_time", "event_end_time")
    def serialize_time(self, value: time) -> str:
        return value.strftime("%H:%M")
