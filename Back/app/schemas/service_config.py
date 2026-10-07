"""Schemas Pydantic para `service_configs` (permanencias de servicios)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ServiceConfigCreate(BaseModel):
    zone_type_id: str
    subtipo: Optional[str] = None
    event_day_id: Optional[str] = None
    average_duration_min: int = Field(gt=0)
    bathroom_use_rate_per_person_hour: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )


class ServiceConfigUpdate(BaseModel):
    average_duration_min: int = Field(gt=0)
    bathroom_use_rate_per_person_hour: Optional[float] = Field(
        default=None, ge=0, allow_inf_nan=False
    )


class ServiceConfigRead(BaseModel):
    id: str
    zone_type_id: str
    subtipo: Optional[str] = None
    event_day_id: Optional[str] = None
    average_duration_min: int
    bathroom_use_rate_per_person_hour: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)