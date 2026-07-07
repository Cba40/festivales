from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ZoneTypeCreate(BaseModel):
    name: str
    slug: str = Field(pattern=r"^[a-z0-9_]+$")
    icon: str
    description: str
    default_factors: dict


class ZoneTypeUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = Field(None, pattern=r"^[a-z0-9_]+$")
    icon: Optional[str] = None
    description: Optional[str] = None
    default_factors: Optional[dict] = None


class ZoneTypeResponse(BaseModel):
    id: str
    name: str
    slug: str
    icon: str
    description: str
    default_factors: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
