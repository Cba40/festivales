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
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ZoneUpdateRequest(BaseModel):
    saturation: str | None = None
    status: str | None = None
    available_capacity: int | None = None
