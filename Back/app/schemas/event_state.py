from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, model_validator


class EventStateCreate(BaseModel):
    event_id: Optional[str] = None
    name: str
    slug: str = Field(pattern=r"^[a-z0-9_]+$")
    sort_order: int
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    description: str
    is_initial: bool = False
    is_final: bool = False
    rules: dict

    @model_validator(mode="after")
    def reject_evento_externo(self):
        if self.rules and self.rules.get("tipo") == "evento_externo":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tipo de regla 'evento_externo' no soportado en P2.0.1. "
                       "Requiere RFC adicional.",
            )
        return self


class EventStateUpdate(BaseModel):
    event_id: Optional[str] = None
    name: Optional[str] = None
    slug: Optional[str] = Field(None, pattern=r"^[a-z0-9_]+$")
    sort_order: Optional[int] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    description: Optional[str] = None
    is_initial: Optional[bool] = None
    is_final: Optional[bool] = None
    rules: Optional[dict] = None

    @model_validator(mode="after")
    def reject_evento_externo(self):
        if self.rules and self.rules.get("tipo") == "evento_externo":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Tipo de regla 'evento_externo' no soportado en P2.0.1. "
                       "Requiere RFC adicional.",
            )
        return self


class EventStateResponse(BaseModel):
    id: str
    event_id: Optional[str] = None
    name: str
    slug: str
    sort_order: int
    color: str
    description: str
    is_initial: bool
    is_final: bool
    rules: dict
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
