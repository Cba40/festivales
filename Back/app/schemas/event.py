# backend/app/schemas/event.py

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EventResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    reference_point_latitude: Optional[float] = None
    reference_point_longitude: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventCreate(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    reference_point_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    reference_point_longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class EventUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    reference_point_latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    reference_point_longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class ActiveEventResponse(BaseModel):
    """Evento que la app debe usar, resuelto desde la jornada activa.

    Lo devuelve `GET /api/events/active` para que el frontend deje de depender de
    una variable de entorno que se hornea en el bundle: el operador marca una
    jornada desde el dashboard y la app sigue al día de evento sin rebuild.
    """

    event_id: str
    event_day_id: str
    event_name: Optional[str] = None
    date: date
    model_config = ConfigDict(from_attributes=True)
