"""Schemas (DTOs) del Product Endpoint de Hospedaje.

Define el contrato público de ``GET /api/events/{event_id}/products/accommodation``.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.accommodation import AccommodationType


class AccommodationItem(BaseModel):
    """DTO de respuesta con los campos del alojamiento + distancia calculada.

    ``distance_km`` solo se completa cuando el usuario provee coordenadas;
    en caso contrario es ``None``.
    """
    id: str
    event_id: str
    name: str
    type: AccommodationType
    address: Optional[str] = None
    reference: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    official_info_url: Optional[str] = None
    active: bool
    distance_km: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AccommodationRecommendationResponse(BaseModel):
    """Respuesta del Product Endpoint de Hospedaje."""
    event_id: str
    accommodations: list[AccommodationItem]
