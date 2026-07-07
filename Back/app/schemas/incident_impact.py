from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class IncidentImpactCreate(BaseModel):
    incident_id: str
    zone_type_id: str
    saturation_delta: float = Field(ge=-1.0, le=1.0)
    attendance_delta: float = Field(ge=-1.0, le=1.0)
    resource_delta: float = Field(ge=-1.0, le=1.0)
    description: Optional[str] = None


class IncidentImpactUpdate(BaseModel):
    incident_id: Optional[str] = None
    zone_type_id: Optional[str] = None
    saturation_delta: Optional[float] = Field(None, ge=-1.0, le=1.0)
    attendance_delta: Optional[float] = Field(None, ge=-1.0, le=1.0)
    resource_delta: Optional[float] = Field(None, ge=-1.0, le=1.0)
    description: Optional[str] = None


class IncidentImpactResponse(BaseModel):
    id: str
    incident_id: str
    zone_type_id: str
    saturation_delta: float
    attendance_delta: float
    resource_delta: float
    description: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
