# backend/app/schemas/exit_product.py
# S2 (Salir V1): DTOs del producto de egreso.
# V1 sin scoring ni ranking: solo salidas vigentes con sus destinos activos.

from pydantic import BaseModel


class ExitDestinationItem(BaseModel):
    id: str
    name: str
    active: bool


class ExitZoneItem(BaseModel):
    zone_id: str
    name: str
    transporte: str  # peatonal | vehicular | transporte (canónica Parte 3)
    lat: float | None = None
    lng: float | None = None
    status: str
    destinations: list[ExitDestinationItem]


class ExitRecommendationResponse(BaseModel):
    event_id: str
    timestamp: str
    zonas: list[ExitZoneItem]
