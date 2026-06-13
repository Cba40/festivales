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
    latitude: float | None = None
    longitude: float | None = None
    disponibilidad: int | None = None
    espera_min: int | None = None
    calle: str | None = None
    subtipo: str | None = None
    tipo_culinario: str | None = None
    x: float | None = None
    y: float | None = None
    direccion: str | None = None
    horario: str | None = None
    telefono: str | None = None
    servicios: str | None = None
    transporte: str | None = None
    capacidad_estimada: int | None = None
    es_embudo: bool | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ZoneCreateRequest(BaseModel):
    name: str
    type: str
    capacity: int
    latitude: float | None = None
    longitude: float | None = None
    disponibilidad: int | None = None
    espera_min: int | None = None
    calle: str | None = None
    subtipo: str | None = None
    tipo_culinario: str | None = None
    x: float | None = None
    y: float | None = None
    direccion: str | None = None
    horario: str | None = None
    telefono: str | None = None
    servicios: str | None = None
    transporte: str | None = None
    capacidad_estimada: int | None = None
    es_embudo: bool | None = None


class ZoneUpdateRequest(BaseModel):
    saturation: str | None = None
    status: str | None = None
    available_capacity: int | None = None
    disponibilidad: int | None = None
    espera_min: int | None = None
    calle: str | None = None
    subtipo: str | None = None
    tipo_culinario: str | None = None
    x: float | None = None
    y: float | None = None
    direccion: str | None = None
    horario: str | None = None
    telefono: str | None = None
    servicios: str | None = None
    transporte: str | None = None
    capacidad_estimada: int | None = None
    es_embudo: bool | None = None


class ZoneConfigUpdateRequest(BaseModel):
    name: str | None = None
    type: str | None = None
    capacity: int | None = None
    available_capacity: int | None = None
    saturation: str | None = None
    latitude: float | None = None
    longitude: float | None = None
