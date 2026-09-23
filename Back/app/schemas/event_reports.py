from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class PeriodRange(BaseModel):
    start: Optional[datetime] = Field(default=None, description="Inicio efectivo del período")
    end: Optional[datetime] = Field(default=None, description="Fin efectivo del período")


class ResultStatusCount(BaseModel):
    result_status: str = Field(..., description="Estado del resultado: ok | empty | unavailable | error")
    count: int = Field(..., description="Cantidad de consultas en ese estado")


class EventSummaryResponse(BaseModel):
    event_id: str = Field(..., description="ID del evento")
    event_name: str = Field(..., description="Nombre del evento")
    period: PeriodRange = Field(..., description="Período cubierto por el informe")
    total_consultas: int = Field(..., description="Total de consultas registradas")
    with_results: int = Field(..., description="Consultas con resultados (status ok)")
    coverage_gaps_empty: int = Field(..., description="Consultas sin resultados por brecha de información (status empty)")
    technical_errors: int = Field(..., description="Consultas con incidencia técnica (status error)")
    breakdown: list[ResultStatusCount] = Field(..., description="Desglose por result_status")


class ServiceBreakdownItem(BaseModel):
    service_category: str = Field(..., description="Categoría de servicio municipal")
    total_consultas: int = Field(..., description="Consultas registradas para la categoría")
    percentage: float = Field(..., description="Porcentaje de consultas registradas (0-100)")


class ServiceBreakdownResponse(BaseModel):
    event_id: str = Field(..., description="ID del evento")
    event_name: str = Field(..., description="Nombre del evento")
    period: PeriodRange = Field(..., description="Período cubierto por el informe")
    services: list[ServiceBreakdownItem] = Field(..., description="Agregación por service_category")


class CoverageGapItem(BaseModel):
    service_category: str = Field(..., description="Categoría de servicio municipal")
    total_consultas: int = Field(..., description="Consultas registradas para la categoría")
    empty_count: int = Field(..., description="Consultas con status empty")
    empty_rate: float = Field(..., description="Proporción empty/total (0-1)")


class TemporalBucket(BaseModel):
    day: date = Field(..., description="Día agrupado (UTC)")
    count: int = Field(..., description="Conteo del día")


class CoverageGapsResponse(BaseModel):
    event_id: str = Field(..., description="ID del evento")
    event_name: str = Field(..., description="Nombre del evento")
    period: PeriodRange = Field(..., description="Período cubierto por el informe")
    services: list[CoverageGapItem] = Field(..., description="Brechas de información por service_category")
    temporal_distribution: list[TemporalBucket] = Field(..., description="Distribución temporal de las brechas empty")


class TechnicalIncidentItem(BaseModel):
    service_category: str = Field(..., description="Categoría de servicio municipal")
    error_count: int = Field(..., description="Consultas con status error")
    error_rate: float = Field(..., description="Proporción error/total (0-1)")


class TechnicalIncidentsResponse(BaseModel):
    event_id: str = Field(..., description="ID del evento")
    event_name: str = Field(..., description="Nombre del evento")
    period: PeriodRange = Field(..., description="Período cubierto por el informe")
    services: list[TechnicalIncidentItem] = Field(..., description="Incidencias técnicas por service_category")
    temporal_distribution: list[TemporalBucket] = Field(..., description="Distribución temporal de las incidencias error")


class TemporalDistributionBucket(BaseModel):
    bucket: datetime = Field(..., description="Inicio del intervalo agrupado, en hora local")
    count: int = Field(..., description="Cantidad de consultas en el intervalo")
    phase: Optional[str] = Field(default=None, description="Fase operativa que cubre el intervalo (solo granularity=hour)")


class TemporalDistributionResponse(BaseModel):
    event_id: str = Field(..., description="ID del evento")
    event_name: str = Field(..., description="Nombre del evento")
    period: PeriodRange = Field(..., description="Período cubierto por el informe")
    granularity: str = Field(..., description="Granularidad temporal: hour | day")
    timezone: str = Field(..., description="Zona horaria local utilizada (IANA)")
    service_category: Optional[str] = Field(default=None, description="Categoría de servicio filtrada (si se especificó)")
    buckets: list[TemporalDistributionBucket] = Field(..., description="Distribución temporal de consultas registradas")


class RecommendedZoneItem(BaseModel):
    zone_id: str = Field(..., description="ID de la zona")
    zone_name: str = Field(..., description="Nombre de la zona")
    zone_type: str = Field(..., description="Tipo de la zona")
    recommendations: int = Field(..., description="Cantidad de recomendaciones en las que aparece la zona")


class RecommendedZonesResponse(BaseModel):
    event_id: str = Field(..., description="ID del evento")
    event_name: str = Field(..., description="Nombre del evento")
    period: PeriodRange = Field(..., description="Período cubierto por el informe")
    service_category: Optional[str] = Field(default=None, description="Categoría de servicio filtrada (si se especificó)")
    zones: list[RecommendedZoneItem] = Field(..., description="Zonas ordenadas por cantidad de recomendaciones")