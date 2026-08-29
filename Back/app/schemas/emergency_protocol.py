"""Schemas (DTOs) del Product Endpoint de Protocolos (Emergencia V2 - S2).

Define el contrato público de ``GET /api/emergency-protocols``.
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.emergency import EmergencyType
from app.models.emergency_protocol import EmergencyProtocolContext


class EmergencyProtocolResponse(BaseModel):
    """DTO de respuesta con un protocolo de emergencia."""
    id: str
    context: EmergencyProtocolContext
    title: str
    description: Optional[str]
    icon: str
    steps: list[str]
    priority: int
    order: int
    target_type: Optional[EmergencyType]
    active: bool

    model_config = ConfigDict(from_attributes=True)


class EmergencyProtocolListResponse(BaseModel):
    """Respuesta del Product Endpoint de Protocolos."""
    context: EmergencyProtocolContext
    protocols: list[EmergencyProtocolResponse]