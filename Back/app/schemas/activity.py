"""Schemas del endpoint público de actividad (Analytics V2).

POST /api/events/{event_id}/activity registra únicamente ``screen_open`` y
``filter_change`` con ``origin`` forzado a ``user``. El cliente NO puede
enviar ``interaction_type=request`` ni campos arbitrarios (``extra="forbid"``).
"""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.service_interaction_log import SERVICE_CATEGORIES

ACTIVITY_INTERACTION_TYPES = Literal["screen_open", "filter_change"]


class ActivityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interaction_type: ACTIVITY_INTERACTION_TYPES = Field(
        ...,
        description="Tipo de evento: screen_open | filter_change",
    )
    service_category: str = Field(
        ...,
        description="Categoría de servicio municipal de la pantalla donde ocurrió",
    )
    request_mode: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Valor semántico: ruta para screen_open (ej. /salir) o clave=valor para filter_change (ej. mode=peatonal)",
    )

    @field_validator("service_category")
    @classmethod
    def _validate_service_category(cls, value: str) -> str:
        if value not in SERVICE_CATEGORIES:
            raise ValueError(f"unknown service_category: {value}")
        return value


class ActivityRecorded(BaseModel):
    event_id: str = Field(..., description="ID del evento")
    interaction_type: str = Field(..., description="screen_open | filter_change")
    service_category: str = Field(..., description="Categoría de servicio registrada")
    request_mode: Optional[str] = Field(default=None, description="Valor semántico registrado")