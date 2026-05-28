# backend/app/schemas/zone.py

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ZoneResponse(BaseModel):
    id: str
    event_id: str
    name: str
    type: str
    saturation: str
    status: str
    capacity: int
    available_capacity: int
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ZoneCreateRequest(BaseModel):
    name: str
    type: str
    capacity: int
    latitude: float | None = None
    longitude: float | None = None


class ZoneUpdateRequest(BaseModel):
    saturation: str | None = None
    status: str | None = None
    available_capacity: int | None = None


class ZoneConfigUpdateRequest(BaseModel):
    name: str | None = None
    type: str | None = None
    capacity: int | None = None
    latitude: float | None = None
    longitude: float | None = None
