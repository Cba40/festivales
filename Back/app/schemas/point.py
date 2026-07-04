# backend/app/schemas/point.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PointResponse(BaseModel):
    id: str
    event_id: str
    name: str
    type: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
