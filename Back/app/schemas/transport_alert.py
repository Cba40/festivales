"""TransportAlert: Alerta operativa inmediata dirigida al público."""
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

AlertType = Literal["info", "warning", "disruption", "closure"]


class TransportAlertCreate(BaseModel):
    """Schema para crear una nueva alerta operativa."""
    event_id: str = Field(max_length=36)
    line_id: Optional[str] = Field(default=None, max_length=36)
    alert_type: AlertType
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    valid_from: datetime
    valid_until: datetime

    @model_validator(mode="after")
    def check_temporal(self) -> "TransportAlertCreate":
        if self.valid_until <= self.valid_from:
            raise ValueError("valid_until must be greater than valid_from")
        return self


class TransportAlertUpdate(BaseModel):
    """Schema para actualizar una alerta operativa existente."""
    line_id: Optional[str] = Field(default=None, max_length=36)
    alert_type: Optional[AlertType] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def check_temporal(self) -> "TransportAlertUpdate":
        if (
            self.valid_from is not None
            and self.valid_until is not None
            and self.valid_until <= self.valid_from
        ):
            raise ValueError("valid_until must be greater than valid_from")
        return self


class TransportAlertResponse(BaseModel):
    """Representación de una alerta operativa."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: str
    line_id: Optional[str]
    alert_type: str
    title: str
    description: str
    valid_from: datetime
    valid_until: datetime
    is_active: bool
    created_at: datetime
    updated_at: datetime