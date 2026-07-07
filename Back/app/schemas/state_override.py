from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class StateOverrideCreate(BaseModel):
    event_day_id: str
    event_state_id: str
    zone_type_id: Optional[str] = None
    start_time: datetime
    end_time: datetime
    reason: str
    created_by: str
    is_active: bool = True


class StateOverrideUpdate(BaseModel):
    event_day_id: Optional[str] = None
    event_state_id: Optional[str] = None
    zone_type_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    reason: Optional[str] = None
    created_by: Optional[str] = None
    is_active: Optional[bool] = None


class StateOverrideResponse(BaseModel):
    id: str
    event_day_id: str
    event_state_id: str
    zone_type_id: Optional[str] = None
    start_time: datetime
    end_time: datetime
    reason: str
    created_by: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
