"""OperationalEventModifier: Configuracion de como un evento altera factores de comportamiento."""
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

EVENT_TYPE_LITERAL = Literal[
    "fin_espectaculo",
    "tormenta",
    "evacuacion",
    "corte_energia",
    "incidente_operativo",
]


class OperationalEventModifierCreate(BaseModel):
    """Schema para crear un nuevo modificador de evento operativo."""
    event_type: EVENT_TYPE_LITERAL
    zone_type_id: str | None = Field(default=None, max_length=36)
    saturation_multiplier: Decimal = Field(gt=0, le=Decimal('999.99'))
    availability_multiplier: Decimal = Field(gt=0, le=Decimal('999.99'))
    priority_modifier: Decimal = Field(ge=Decimal('-999.99'), le=Decimal('999.99'))


class OperationalEventModifierUpdate(BaseModel):
    """Schema para actualizar un modificador existente.
    event_type y zone_type_id son inmutables una vez creados.
    """
    saturation_multiplier: Decimal | None = Field(default=None, gt=0, le=Decimal('999.99'))
    availability_multiplier: Decimal | None = Field(default=None, gt=0, le=Decimal('999.99'))
    priority_modifier: Decimal | None = Field(default=None, ge=Decimal('-999.99'), le=Decimal('999.99'))


class OperationalEventModifierResponse(BaseModel):
    """Representacion de un modificador de evento operativo."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    zone_type_id: str | None
    saturation_multiplier: Decimal
    availability_multiplier: Decimal
    priority_modifier: Decimal
