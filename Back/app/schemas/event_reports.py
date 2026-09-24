from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

PeriodMode = Literal["requested", "event", "accumulated"]


class PeriodRange(BaseModel):
    start: Optional[datetime] = Field(default=None, description="Inicio efectivo del período")
    end: Optional[datetime] = Field(default=None, description="Fin efectivo del período")
    mode: Optional[PeriodMode] = Field(
        default=None,
        description=(
            "Origen del período efectivo: requested (start/end explícitos), "
            "event (Event.start_date/end_date), accumulated (histórico, sin filtro de rango)"
        ),
    )


class ResultStatusCount(BaseModel):
    result_status: str = Field(..., description="Estado del resultado: ok | empty | unavailable | error")
    count: int = Field(..., description="Cantidad de actividades del usuario en ese estado")


class EventSummaryResponse(BaseModel):
    event_id: str = Field(..., description="ID del evento")
    event_name: str = Field(..., description="Nombre del evento")
    period: PeriodRange = Field(..., description="Período cubierto por el informe")
    total_consultas: int = Field(..., description="Total de actividad real del usuario (screen_open/filter_change con origin=user)")
    with_results: int = Field(..., description="Actividad de usuario con resultado ok")
    coverage_gaps_empty: int = Field(..., description="Actividad de usuario sin resultados por brecha de información (status empty)")
    technical_errors: int = Field(..., description="Actividad de usuario con status error")
    breakdown: list[ResultStatusCount] = Field(..., description="Desglose de la actividad por result_status")


class ServiceBreakdownItem(BaseModel):
    service_category: str = Field(..., description="Categoría de servicio municipal")
    total_consultas: int = Field(..., description="Actividad real del usuario registrada para la categoría")
    percentage: float = Field(..., description="Porcentaje de actividad del usuario registrada (0-100)")


class ServiceBreakdownResponse(BaseModel):
    event_id: str = Field(..., description="ID del evento")
    event_name: str = Field(..., description="Nombre del evento")
    period: PeriodRange = Field(..., description="Período cubierto por el informe")
    services: list[ServiceBreakdownItem] = Field(..., description="Agregación por service_category")


class CoverageGapItem(BaseModel):
    service_category: str = Field(..., description="Categoría de servicio municipal")
    total_consultas: int = Field(..., description="Requests técnicas registradas para la categoría")
    empty_count: int = Field(..., description="Requests con status empty")
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
    error_count: int = Field(..., description="Requests con status error")
    error_rate: float = Field(..., description="Proporción error/total (0-1)")


class TechnicalIncidentsResponse(BaseModel):
    event_id: str = Field(..., description="ID del evento")
    event_name: str = Field(..., description="Nombre del evento")
    period: PeriodRange = Field(..., description="Período cubierto por el informe")
    services: list[TechnicalIncidentItem] = Field(..., description="Incidencias técnicas por service_category")
    temporal_distribution: list[TemporalBucket] = Field(..., description="Distribución temporal de las incidencias error")


class TemporalDistributionBucket(BaseModel):
    bucket: datetime = Field(..., description="Inicio del intervalo agrupado, en hora local")
    count: int = Field(..., description="Cantidad de actividades del usuario en el intervalo")
    phase: Optional[str] = Field(default=None, description="Fase operativa que cubre el intervalo (solo granularity=hour)")


class TemporalDistributionResponse(BaseModel):
    event_id: str = Field(..., description="ID del evento")
    event_name: str = Field(..., description="Nombre del evento")
    period: PeriodRange = Field(..., description="Período cubierto por el informe")
    granularity: str = Field(..., description="Granularidad temporal: hour | day")
    timezone: str = Field(..., description="Zona horaria local utilizada (IANA)")
    service_category: Optional[str] = Field(default=None, description="Categoría de servicio filtrada (si se especificó)")
    buckets: list[TemporalDistributionBucket] = Field(..., description="Distribución temporal de la actividad real del usuario")


class RecommendedZoneItem(BaseModel):
    zone_id: str = Field(..., description="ID de la zona")
    zone_name: str = Field(..., description="Nombre de la zona")
    zone_type: str = Field(..., description="Tipo de la zona")
    recommendations: int = Field(..., description="Cantidad de requests técnicas en las que aparece la zona")


class RecommendedZonesResponse(BaseModel):
    event_id: str = Field(..., description="ID del evento")
    event_name: str = Field(..., description="Nombre del evento")
    period: PeriodRange = Field(..., description="Período cubierto por el informe")
    service_category: Optional[str] = Field(default=None, description="Categoría de servicio filtrada (si se especificó)")
    zones: list[RecommendedZoneItem] = Field(..., description="Zonas ordenadas por cantidad de recomendaciones")


class OperationalPhaseRef(BaseModel):
    phase_id: Optional[str] = Field(default=None, description="ID de la fase operativa (null = no asignable)")
    phase_name: str = Field(..., description="Nombre de la fase (o 'unassigned')")


class PlatformQueriesPhase(OperationalPhaseRef):
    consultas_total: int = Field(..., description="Actividad real del usuario registrada en la fase")
    with_results: int = Field(..., description="Actividad de usuario con resultado ok")
    empty: int = Field(..., description="Actividad de usuario sin resultados por brecha (status empty)")
    unavailable: int = Field(..., description="Actividad de usuario sin servicio disponible (status unavailable)")
    error: int = Field(..., description="Actividad de usuario con status error")


class ZonePredictionSummary(BaseModel):
    zone_id: Optional[str] = Field(default=None, description="ID de la zona")
    zone_name: str = Field(..., description="Nombre de la zona (fallback: id)")
    projected_density: Optional[int] = Field(default=None, description="Densidad proyectada (estado más reciente)")
    operational_state: Optional[str] = Field(default=None, description="Estado operacional proyectado")


class PredictionsPhase(OperationalPhaseRef):
    predictions_count: int = Field(..., description="Cantidad de predicciones persistidas asignadas a la fase")
    zones: list[ZonePredictionSummary] = Field(..., description="Estado proyectado por zona (más reciente en la fase)")


class ZoneObservationSummary(BaseModel):
    zone_id: str = Field(..., description="ID de la zona")
    zone_name: str = Field(..., description="Nombre de la zona (fallback: id)")
    observations_count: int = Field(..., description="Observaciones en la fase para la zona")
    observed_density_total: int = Field(..., description="Suma de densidad observada")
    observed_density_avg: Optional[float] = Field(default=None, description="Promedio de densidad observada")


class ObservationsPhase(OperationalPhaseRef):
    observations_count: int = Field(..., description="Cantidad de observaciones asignadas a la fase")
    zones: list[ZoneObservationSummary] = Field(..., description="Densidad observada por zona")


class OperationalEventSummaryItem(BaseModel):
    operational_event_id: str = Field(..., description="ID del evento operativo")
    event_type: str = Field(..., description="Tipo de evento operativo")
    is_incident: bool = Field(..., description="Si es incidente (is_incident)")
    zone_id: Optional[str] = Field(default=None, description="ID de la zona afectada")
    zone_name: Optional[str] = Field(default=None, description="Nombre de la zona afectada")
    start_timestamp: datetime = Field(..., description="Inicio del evento operativo (UTC)")
    end_timestamp: datetime = Field(..., description="Fin del evento operativo (UTC)")
    description: Optional[str] = Field(default=None, description="Descripción")


class OperationalEventsPhase(OperationalPhaseRef):
    total_events: int = Field(..., description="Eventos operativos asignados a la fase")
    incidents: int = Field(..., description="Incidentes (is_incident = true) en la fase")
    events: list[OperationalEventSummaryItem] = Field(..., description="Detalle de eventos (asignados por inicio)")


class OperationalProfileResponse(BaseModel):
    event_id: str = Field(..., description="ID del evento")
    event_name: str = Field(..., description="Nombre del evento")
    timezone: str = Field(..., description="Zona horaria local usada (IANA)")
    operational_profile_id: Optional[str] = Field(default=None, description="Perfil operativo si las jornadas comparten uno")
    phases: list[OperationalPhaseRef] = Field(..., description="Fases operativas presentes en el informe")
    platform_queries: list[PlatformQueriesPhase] = Field(..., description="Actividad real del usuario por fase")
    predictions_summary: list[PredictionsPhase] = Field(..., description="Predicciones persistidas por fase")
    observations_summary: list[ObservationsPhase] = Field(..., description="Observaciones operativas por fase")
    operational_events_summary: list[OperationalEventsPhase] = Field(..., description="Eventos/incidencias operativas por fase")
    insufficient_data: list[str] = Field(..., description="Notas de disponibilidad / faltante de correspondencia temporal")