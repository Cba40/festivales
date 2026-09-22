"""OperatorMessage: Mensaje programable del operador para el público."""
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

MessageStatus = Literal["draft", "published", "cancelled"]
MessagePriority = Literal["normal", "high", "urgent"]


class OperatorMessageCreate(BaseModel):
    """Schema para crear un nuevo mensaje del operador."""
    event_id: str = Field(max_length=36)
    line_id: Optional[str] = Field(default=None, max_length=36)
    status: MessageStatus = "draft"
    priority: MessagePriority = "normal"
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    publish_at: datetime
    expires_at: Optional[datetime] = None

    @model_validator(mode="after")
    def check_temporal(self) -> "OperatorMessageCreate":
        if self.expires_at is not None and self.expires_at <= self.publish_at:
            raise ValueError("expires_at must be greater than publish_at")
        return self


class OperatorMessageUpdate(BaseModel):
    """Schema para actualizar un mensaje del operador existente."""
    line_id: Optional[str] = Field(default=None, max_length=36)
    status: Optional[MessageStatus] = None
    priority: Optional[MessagePriority] = None
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    @model_validator(mode="after")
    def check_temporal(self) -> "OperatorMessageUpdate":
        if (
            self.publish_at is not None
            and self.expires_at is not None
            and self.expires_at <= self.publish_at
        ):
            raise ValueError("expires_at must be greater than publish_at")
        return self


class OperatorMessageResponse(BaseModel):
    """Representación de un mensaje del operador."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_id: str
    line_id: Optional[str]
    status: str
    priority: str
    title: str
    description: str
    publish_at: datetime
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime