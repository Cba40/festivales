from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class OperationalObservationCreate(BaseModel):
    """Alta de una observacion de campo.

    `observer_id` NO esta en el DTO. El servidor lo inyecta desde el usuario autenticado.
    """

    event_day_id: str = Field(..., description="ID del event day")
    zone_id: str = Field(..., description="ID de la zona")
    timestamp: datetime = Field(..., description="Timestamp timezone-aware")
    observed_density: int = Field(..., ge=0, description="Densidad observada (>= 0)")
    source: str = Field(default="manual", description="Fuente: manual, sensor, official_report")
    metadata: Optional[dict] = Field(default=None, description="Metadatos adicionales")

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class OperationalObservationUpdate(BaseModel):
    """Corrección in-place de una observación (RFC-006).

    `extra="forbid"` no es cosmético: `timestamp`, `zone_id`, `event_day_id` y `observer_id`
    son inmutables por decisión de diseño. Con `forbid`, mandar cualquiera de esos campos
    es un 422 explícito en vez de un ignore silencioso que el cliente interpreta como un éxito.

    `corrected_by` y `observer_id` NO se aceptan desde el body: los escribe el servidor con la
    identidad del token. Aceptarlos acá haría que un campo de auditoría fuera arbitrariamente
    seteable por el cliente.
    """

    model_config = ConfigDict(extra="forbid")

    observed_density: Optional[int] = Field(None, ge=0, description="Densidad observada (>= 0)")
    source: Optional[str] = Field(None, description="Fuente: manual, sensor, official_report")
    metadata: Optional[dict] = Field(None, description="Metadatos rewritten por el operador")

    @model_validator(mode="after")
    def at_least_one_field(self) -> "OperationalObservationUpdate":
        if (
            self.observed_density is None
            and self.source is None
            and self.metadata is None
        ):
            raise ValueError("PATCH vacío: indicá al menos un campo a corregir")
        return self


class OperationalObservationResponse(BaseModel):
    id: str = Field(..., description="ID de la observación")
    event_day_id: str = Field(..., description="ID del event day")
    zone_id: str = Field(..., description="ID de la zona")
    timestamp: datetime = Field(..., description="Timestamp de la observación")
    observed_density: int = Field(..., ge=0, description="Densidad observada")
    observer_id: Optional[str] = Field(default=None, description="ID del observador")
    source: str = Field(default="manual", description="Fuente de la observación")
    metadata: Optional[dict] = Field(default=None, description="Metadatos adicionales")
    created_at: datetime = Field(..., description="Fecha de creación")
    corrected_by: Optional[str] = Field(
        default=None, description="Usuario que corrigió la observación (sub del token)"
    )
    corrected_at: Optional[datetime] = Field(
        default=None, description="Momento de la corrección"
    )

    model_config = ConfigDict(from_attributes=True)