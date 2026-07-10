"""ZoneBehavior: Comportamiento esperado de un ZoneType durante una OperationalPhase."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ZoneBehaviorCreate(BaseModel):
    """Schema para crear un nuevo comportamiento de zona."""
    operational_phase_id: UUID
    zone_type_id: str = Field(max_length=36)
    saturation_factor: Decimal = Field(gt=0, le=Decimal('999.99'))
    availability_factor: Decimal = Field(gt=0, le=Decimal('999.99'))
    resource_factor: Decimal = Field(gt=0, le=Decimal('999.99'))
    priority_weight: Decimal = Field(gt=0, le=Decimal('999.99'))


class ZoneBehaviorUpdate(BaseModel):
    """Schema para actualizar un comportamiento de zona existente.
    operational_phase_id y zone_type_id son inmutables una vez creados.
    """
    saturation_factor: Decimal | None = Field(default=None, gt=0, le=Decimal('999.99'))
    availability_factor: Decimal | None = Field(default=None, gt=0, le=Decimal('999.99'))
    resource_factor: Decimal | None = Field(default=None, gt=0, le=Decimal('999.99'))
    priority_weight: Decimal | None = Field(default=None, gt=0, le=Decimal('999.99'))


class ZoneBehaviorResponse(BaseModel):
    """Representacion de un comportamiento de zona."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    operational_phase_id: UUID
    zone_type_id: str
    saturation_factor: Decimal
    availability_factor: Decimal
    resource_factor: Decimal
    priority_weight: Decimal
    created_at: datetime
    updated_at: datetime
