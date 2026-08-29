"""DTOs de gestión administrativa de Emergencia V1 (Dashboard > Infraestructura > Emergencias).

Complementa al modelo Emergency (S1) con su contrato CRUD/admin. El tipo se
valida con el enum canónico ``EmergencyType`` (política/bomberos/salud/etc.).

Incluye también ``CityResponse`` para que el panel admin pueda listar las
ciudades y ofrecer un selector al operador (el módulo es transversal por ciudad).
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.emergency import EmergencyType


class CityCreate(BaseModel):
    """DTO de creación de una ciudad (nombre requerido; provincia/país opcionales)."""
    name: str = Field(..., min_length=1, max_length=100)
    province: Optional[str] = None
    country: str = Field(default="Argentina", max_length=100)


class CityResponse(BaseModel):
    """DTO mínimo de respuesta de una ciudad (id + nombre para el selector)."""
    id: str
    name: str
    province: Optional[str] = None
    country: str

    model_config = ConfigDict(from_attributes=True)


class EmergencyCreate(BaseModel):
    city_id: str
    name: str = Field(..., min_length=1, max_length=255)
    type: EmergencyType
    phone: Optional[str] = None
    emergency_number: Optional[str] = None
    address: Optional[str] = None
    reference: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0)
    services: Optional[str] = None
    schedule: Optional[str] = None
    active: bool = True


class EmergencyUpdate(BaseModel):
    city_id: Optional[str] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[EmergencyType] = None
    phone: Optional[str] | None = None
    emergency_number: Optional[str] | None = None
    address: Optional[str] | None = None
    reference: Optional[str] | None = None
    latitude: Optional[float] | None = Field(None, ge=-90.0, le=90.0)
    longitude: Optional[float] | None = Field(None, ge=-180.0, le=180.0)
    services: Optional[str] | None = None
    schedule: Optional[str] | None = None
    active: Optional[bool] = None


class EmergencyResponse(BaseModel):
    id: str
    city_id: str
    name: str
    type: EmergencyType
    phone: Optional[str]
    emergency_number: Optional[str]
    address: Optional[str]
    reference: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    services: Optional[str]
    schedule: Optional[str]
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
