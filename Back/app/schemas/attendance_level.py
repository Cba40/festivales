from typing import Optional

from pydantic import BaseModel, ConfigDict


class AttendanceLevelCreate(BaseModel):
    event_day_id: str
    name: str
    min_people: int
    max_people: Optional[int] = None


class AttendanceLevelUpdate(BaseModel):
    name: Optional[str] = None
    min_people: Optional[int] = None
    max_people: Optional[int] = None


class AttendanceLevelResponse(BaseModel):
    id: str
    event_day_id: str
    name: str
    min_people: int
    max_people: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)