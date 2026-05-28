# backend/app/schemas/incident.py

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class IncidentCreate(BaseModel):
    type: str
    severity: str
    description: str
    zone_id: str | None = None


class IncidentResponse(BaseModel):
    id: str
    event_id: str
    type: str
    severity: str
    description: str
    status: str
    zone_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
