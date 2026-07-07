from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EventDayZoneFactorCreate(BaseModel):
    event_day_id: str
    zone_type_id: str
    event_state_id: str
    saturation_factor: float = Field(ge=0.0, le=2.0)
    attendance_factor: float = Field(ge=0.0, le=2.0)
    resource_factor: float = Field(ge=0.0, le=2.0)
    priority_weight: int = Field(ge=0, le=100)
    description: Optional[str] = None


class EventDayZoneFactorUpdate(BaseModel):
    event_day_id: Optional[str] = None
    zone_type_id: Optional[str] = None
    event_state_id: Optional[str] = None
    saturation_factor: Optional[float] = Field(None, ge=0.0, le=2.0)
    attendance_factor: Optional[float] = Field(None, ge=0.0, le=2.0)
    resource_factor: Optional[float] = Field(None, ge=0.0, le=2.0)
    priority_weight: Optional[int] = Field(None, ge=0, le=100)
    description: Optional[str] = None


class EventDayZoneFactorResponse(BaseModel):
    id: str
    event_day_id: str
    zone_type_id: str
    event_state_id: str
    saturation_factor: float
    attendance_factor: float
    resource_factor: float
    priority_weight: int
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
