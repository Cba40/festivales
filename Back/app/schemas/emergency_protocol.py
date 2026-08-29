"""Schemas (DTOs) de Protocolos de Emergencia (Emergencia V2).

S2 define el contrato público de ``GET /api/emergency-protocols``
(``EmergencyProtocolResponse``). S5 agrega los DTOs de escritura del CRUD
admin (Dashboard > Infraestructura > Protocolos de Emergencia): el operador
crea/edita el catálogo sin ``event_id`` ni ``city_id`` (el catálogo es
transversal y contextual por ``context``).
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

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


class ProtocolCreate(BaseModel):
    """DTO de creación de un protocolo (CRUD admin S5)."""
    context: EmergencyProtocolContext
    title: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon: str = Field(..., min_length=1, max_length=10)
    steps: list[str] = Field(default_factory=list)
    priority: int = Field(..., ge=1, le=3)
    order: int = Field(default=0, ge=0)
    target_type: Optional[EmergencyType] = None
    active: bool = True


class ProtocolUpdate(BaseModel):
    """DTO de actualización de un protocolo (CRUD admin S5). Todos opcionales."""
    context: Optional[EmergencyProtocolContext] = None
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, min_length=1, max_length=10)
    steps: Optional[list[str]] = None
    priority: Optional[int] = Field(None, ge=1, le=3)
    order: Optional[int] = Field(None, ge=0)
    target_type: Optional[EmergencyType] = None
    active: Optional[bool] = None