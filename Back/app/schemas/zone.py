# backend/app/schemas/zone.py

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ZoneResponse(BaseModel):
    id: str
    event_id: str
    name: str
    type: str
    saturation: str
    status: str
    capacity: int
    available_capacity: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    disponibilidad: Optional[int] = None
    espera_min: Optional[int] = None
    calle: Optional[str] = None
    subtipo: Optional[str] = None
    tipo_culinario: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    direccion: Optional[str] = None
    horario: Optional[str] = None
    telefono: Optional[str] = None
    servicios: Optional[str] = None
    transporte: Optional[str] = None
    capacidad_estimada: Optional[int] = None
    es_embudo: Optional[bool] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ZoneCreateRequest(BaseModel):
    name: str
    type: str
    capacity: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    disponibilidad: Optional[int] = None
    espera_min: Optional[int] = None
    calle: Optional[str] = None
    subtipo: Optional[str] = None
    tipo_culinario: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    direccion: Optional[str] = None
    horario: Optional[str] = None
    telefono: Optional[str] = None
    servicios: Optional[str] = None
    transporte: Optional[str] = None
    capacidad_estimada: Optional[int] = None
    es_embudo: Optional[bool] = None


class ZoneUpdateRequest(BaseModel):
    saturation: Optional[str] = None
    status: Optional[str] = None
    available_capacity: Optional[int] = None
    disponibilidad: Optional[int] = None
    espera_min: Optional[int] = None
    calle: Optional[str] = None
    subtipo: Optional[str] = None
    tipo_culinario: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    direccion: Optional[str] = None
    horario: Optional[str] = None
    telefono: Optional[str] = None
    servicios: Optional[str] = None
    transporte: Optional[str] = None
    capacidad_estimada: Optional[int] = None
    es_embudo: Optional[bool] = None


class ZoneConfigUpdateRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    capacity: Optional[int] = None
    available_capacity: Optional[int] = None
    saturation: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
