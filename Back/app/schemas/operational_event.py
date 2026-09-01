"""OperationalEvent: Hechos reales ocurridos durante una jornada."""
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

EventType = Literal[
    "accidente",
    "corte_energia",
    "evacuacion",
    "incendio",
    "congestion_extraordinaria",
    "escenario_finalizado",
    "apertura_extraordinaria",
    "corte_calle",
    "fin_espectaculo",
    "tormenta",
    "incidente_operativo",
]

EffectType = Literal[
    "reduccion_capacidad",
    "cierre_total",
    "aumento_demanda",
    "incidente_sin_impacto",
]


def _validate_effect(effect_type, effect_value):
    if effect_value is None and effect_type in ("reduccion_capacidad", "aumento_demanda"):
        raise ValueError(f"effect_value is required for {effect_type}")
    if effect_type == "reduccion_capacidad" and not (1 <= effect_value <= 100):
        raise ValueError("effect_value must be between 1 and 100 for reduccion_capacidad")
    if effect_type == "cierre_total" and effect_value is not None:
        raise ValueError("effect_value must be NULL for cierre_total")
    if effect_type == "aumento_demanda" and effect_value < 1:
        raise ValueError("effect_value must be >= 1 for aumento_demanda")
    if effect_type == "incidente_sin_impacto" and effect_value is not None:
        raise ValueError("effect_value must be NULL for incidente_sin_impacto")


class OperationalEventCreate(BaseModel):
    """Schema para crear un nuevo evento operativo."""
    event_day_id: str = Field(max_length=36)
    zone_id: str = Field(max_length=36)
    event_type: EventType
    description: Optional[str] = Field(default=None, max_length=1000)
    effect_type: EffectType
    effect_value: Optional[int] = None
    is_incident: bool = False
    start_timestamp: datetime
    end_timestamp: datetime

    @model_validator(mode="after")
    def check_temporal(self) -> "OperationalEventCreate":
        if self.end_timestamp <= self.start_timestamp:
            raise ValueError("end_timestamp must be greater than start_timestamp")
        return self

    @model_validator(mode="after")
    def check_effect(self) -> "OperationalEventCreate":
        _validate_effect(self.effect_type, self.effect_value)
        return self


class OperationalEventUpdate(BaseModel):
    """Schema para actualizar un evento operativo existente."""
    event_type: Optional[EventType] = None
    description: Optional[str] = Field(default=None, max_length=1000)
    effect_type: Optional[EffectType] = None
    effect_value: Optional[int] = None
    is_incident: Optional[bool] = None
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None

    @model_validator(mode="after")
    def check_temporal(self) -> "OperationalEventUpdate":
        if (
            self.start_timestamp is not None
            and self.end_timestamp is not None
            and self.end_timestamp <= self.start_timestamp
        ):
            raise ValueError("end_timestamp must be greater than start_timestamp")
        return self

    @model_validator(mode="after")
    def check_effect(self) -> "OperationalEventUpdate":
        if self.effect_type is not None:
            _validate_effect(self.effect_type, self.effect_value)
        return self


class OperationalEventResponse(BaseModel):
    """Representacion de un evento operativo."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_day_id: str
    zone_id: str
    event_type: str
    description: Optional[str]
    effect_type: str
    effect_value: Optional[int]
    is_incident: bool
    start_timestamp: datetime
    end_timestamp: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime
