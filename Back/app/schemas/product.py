from pydantic import BaseModel, Field


class ZonaEstacionamientoItem(BaseModel):
    zone_id: str
    name: str
    score: float = Field(ge=0.0, le=1.0)
    reasoning: list[str]
    saturation_level: float = Field(ge=0.0, le=1.0)
    estado: str
    availability: int
    disponibilidad: int = Field(ge=0, le=100)
    estimated_wait: int
    confidence: float = Field(ge=0.0, le=1.0)
    active_restriction: str
    operational_state: str
    lat: float | None = None
    lng: float | None = None
    referencia: str = ""
    distancia_min: int | None = None


class ParkingRecommendationResponse(BaseModel):
    event_id: str
    timestamp: str
    mode: str
    zonas: list[ZonaEstacionamientoItem]
