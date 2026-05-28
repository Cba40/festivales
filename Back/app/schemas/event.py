# backend/app/schemas/event.py

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EventResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    location: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
