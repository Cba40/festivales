from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ZoneSubtypeResponse(BaseModel):
    id: str
    zone_type_id: str
    slug: str
    name: str
    icon: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    sort_order: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
