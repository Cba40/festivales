# backend/app/schemas/event.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EventResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
