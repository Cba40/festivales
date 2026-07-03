from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class EventDayCreate(BaseModel):
    date: date
    day_of_week: str
    weather: str | None = None
    headliner_artist: str | None = None
    expected_attendance: int | None = None
    peak_hour_start: int | None = None
    peak_hour_end: int | None = None
    opening_time: int | None = None
    closing_time: int | None = None
    notes: str | None = None
    is_active: bool = True


class EventDayUpdate(BaseModel):
    date: date | None = None
    day_of_week: str | None = None
    weather: str | None = None
    headliner_artist: str | None = None
    expected_attendance: int | None = None
    peak_hour_start: int | None = None
    peak_hour_end: int | None = None
    opening_time: int | None = None
    closing_time: int | None = None
    notes: str | None = None
    is_active: bool | None = None


class EventDayResponse(BaseModel):
    id: str
    event_id: str
    date: date
    day_of_week: str
    weather: str | None
    headliner_artist: str | None
    expected_attendance: int | None
    peak_hour_start: int | None
    peak_hour_end: int | None
    opening_time: int | None
    closing_time: int | None
    notes: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventDaySummary(BaseModel):
    id: str
    date: date
    day_of_week: str
    weather: str | None
    headliner_artist: str | None
    expected_attendance: int | None
    is_active: bool
