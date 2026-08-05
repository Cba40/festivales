# backend/app/schemas/event.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EventResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    reference_point_latitude: Optional[float] = None
    reference_point_longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventCreate(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    reference_point_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    reference_point_longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class EventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    reference_point_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    reference_point_longitude: Optional[float] = Field(default=None, ge=-180, le=180)
