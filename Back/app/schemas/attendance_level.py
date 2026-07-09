from typing import Optional

from pydantic import BaseModel, ConfigDict


class AttendanceLevelCreate(BaseModel):
    name: str
    min_people: int
    max_people: Optional[int] = None
    global_multiplier: float


class AttendanceLevelUpdate(BaseModel):
    name: Optional[str] = None
    min_people: Optional[int] = None
    max_people: Optional[int] = None
    global_multiplier: Optional[float] = None


class AttendanceLevelResponse(BaseModel):
    id: str
    event_id: str
    name: str
    min_people: int
    max_people: Optional[int] = None
    global_multiplier: float

    model_config = ConfigDict(from_attributes=True)
