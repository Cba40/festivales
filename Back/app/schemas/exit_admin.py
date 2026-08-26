# backend/app/schemas/exit_admin.py
# DTOs de gestión de destinos de salida (Dashboard - Infraestructura).
# Complementa al modelo ExitDestination (Salir V1) con su contrato CRUD.

from pydantic import BaseModel, ConfigDict


class ExitDestinationCreate(BaseModel):
    name: str
    active: bool = True


class ExitDestinationUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None


class ExitDestinationResponse(BaseModel):
    id: str
    event_id: str
    name: str
    active: bool

    model_config = ConfigDict(from_attributes=True)


class ZoneExitDestinationsUpdate(BaseModel):
    destination_ids: list[str]


class ZoneExitDestinationsResponse(BaseModel):
    zone_id: str
    destination_ids: list[str]
