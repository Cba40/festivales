"""Schemas (DTOs) del Product Endpoint de Emergencia.

Define el contrato público de ``GET /api/emergencies``.
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.emergency import EmergencyType


class EmergencyItem(BaseModel):
    """DTO de respuesta con los campos del punto de emergencia + distancia.

    ``distance_km`` solo se completa cuando el usuario provee coordenadas y la
    emergencia tiene ubicación física; en caso contrario es ``None`` (p. ej. los
    números de emergencia 911 / 107 / 100 que no tienen lat/long).
    """
    id: str
    name: str
    type: EmergencyType
    phone: Optional[str] = None
    emergency_number: Optional[str] = None
    address: Optional[str] = None
    reference: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    services: Optional[str] = None
    schedule: Optional[str] = None
    active: bool
    distance_km: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class EmergencyRecommendationResponse(BaseModel):
    """Respuesta del Product Endpoint de Emergencia."""
    emergencies: list[EmergencyItem]
