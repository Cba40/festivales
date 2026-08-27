# backend/app/schemas/transport_admin.py
# DTOs de gestión administrativa de Transporte V1 (Dashboard > Infraestructura > Transporte).
# Complementa al modelo TransportLine (S1) con su contrato CRUD/admin.
#
# Los horarios viven en transport_schedules (asociados a line_stop_id), el
# destino en transport_schedules.destination (NO hay tabla line_destinations).

from typing import Literal

from pydantic import BaseModel, ConfigDict


class TransportLineCreate(BaseModel):
    name: str
    type: Literal["urbano", "interurbano"]
    company: str
    color: str | None = None
    active: bool = True


class TransportLineUpdate(BaseModel):
    name: str | None = None
    type: Literal["urbano", "interurbano"] | None = None
    company: str | None = None
    color: str | None = None
    active: bool | None = None


class TransportLineResponse(BaseModel):
    id: str
    event_id: str
    name: str
    type: str
    company: str
    color: str | None
    active: bool

    model_config = ConfigDict(from_attributes=True)


class LineStopCreate(BaseModel):
    zone_id: str
    stop_order: int


class LineStopResponse(BaseModel):
    id: str
    line_id: str
    zone_id: str
    zone_name: str
    stop_order: int


class LineStopsUpdate(BaseModel):
    stops: list[LineStopCreate]  # reemplazo completo (idempotente)


class ScheduleCreate(BaseModel):
    line_stop_id: str
    day_type: Literal["weekday", "saturday", "sunday_holiday"]
    departure_time: str  # "HH:MM"
    destination: str


class ScheduleResponse(BaseModel):
    id: str
    line_stop_id: str
    day_type: str
    departure_time: str  # "HH:MM"
    destination: str


class SchedulesUpdate(BaseModel):
    schedules: list[ScheduleCreate]  # reemplazo completo


class CsvImportResponse(BaseModel):
    lines_created: int
    lines_updated: int
    stops_created: int
    schedules_created: int
    errors: list[str]
