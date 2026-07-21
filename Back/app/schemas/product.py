from pydantic import BaseModel, Field


class ZonaItemBase(BaseModel):
    zone_id: str
    name: str
    score: float = Field(ge=0.0, le=1.0)
    reasoning: list[str]
    saturation_level: float = Field(ge=0.0, le=1.0)
    estado: str
    availability: int
    estimated_wait: int
    confidence: float = Field(ge=0.0, le=1.0)
    active_restriction: str
    operational_state: str
    lat: float | None = None
    lng: float | None = None
    referencia: str = ""
    distancia_min: int | None = None


class ZonaEstacionamientoItem(ZonaItemBase):
    pass


class ParkingRecommendationResponse(BaseModel):
    event_id: str
    timestamp: str
    mode: str
    zonas: list[ZonaEstacionamientoItem]


class ZonaGastronomicaItem(ZonaItemBase):
    categoria: str = ""


class ZonaTransporteItem(ZonaItemBase):
    calle: str = ""


class GastronomyRecommendationResponse(BaseModel):
    event_id: str
    timestamp: str
    mode: str
    zonas: list[ZonaGastronomicaItem]


class ZonaSanitaryItem(ZonaItemBase):
    pass


class TransportRecommendationResponse(BaseModel):
    event_id: str
    timestamp: str
    mode: str
    zonas: list[ZonaTransporteItem]


class ZonaRestItem(ZonaItemBase):
    pass


class BathroomRecommendationResponse(BaseModel):
    event_id: str
    timestamp: str
    mode: str
    zonas: list[ZonaSanitaryItem]


class ZonaSaludItem(ZonaItemBase):
    pass


class RestRecommendationResponse(BaseModel):
    event_id: str
    timestamp: str
    mode: str
    zonas: list[ZonaRestItem]


class ZonaHidratacionItem(ZonaItemBase):
    pass


class HealthRecommendationResponse(BaseModel):
    event_id: str
    timestamp: str
    mode: str
    zonas: list[ZonaSaludItem]


class HydrationRecommendationResponse(BaseModel):
    event_id: str
    timestamp: str
    mode: str
    zonas: list[ZonaHidratacionItem]
