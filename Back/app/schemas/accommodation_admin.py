"""DTOs de gestión administrativa de Hospedaje V1 (Dashboard > Infraestructura > Hospedaje).

Complementa al modelo Accommodation (S1) con su contrato CRUD/admin. El tipo
se valida estrictamente como Literal (hotel/hostel/camping/other), reflejando
el enum ``AccommodationType`` del modelo.
"""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


AccommodationAdminType = Literal["hotel", "hostel", "camping", "other"]


class AccommodationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: AccommodationAdminType
    address: Optional[str] = None
    reference: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    phone: Optional[str] = None
    website: Optional[str] = None
    official_info_url: Optional[str] = None
    active: bool = True


class AccommodationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[AccommodationAdminType] = None
    address: Optional[str] | None = None
    reference: Optional[str] | None = None
    latitude: Optional[float] | None = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] | None = Field(None, ge=-180.0, le=180.0)
    phone: Optional[str] | None = None
    website: Optional[str] | None = None
    official_info_url: Optional[str] | None = None
    active: Optional[bool] = None


class AccommodationResponse(BaseModel):
    id: str
    event_id: str
    name: str
    type: str
    address: Optional[str]
    reference: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    phone: Optional[str]
    website: Optional[str]
    official_info_url: Optional[str]
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
