"""OperationalProfile: Patron operativo esperado de una jornada."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OperationalProfileCreate(BaseModel):
    """Schema para crear un nuevo perfil operativo."""
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class OperationalProfileUpdate(BaseModel):
    """Schema para actualizar un perfil operativo existente."""
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)


class OperationalProfileResponse(BaseModel):
    """Representacion de un perfil operativo."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
