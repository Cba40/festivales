from __future__ import annotations

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .recommendation_supporting_metrics import SupportingMetricsSchema
from .recommendation_historic_trace import HistoricTraceSchema
from ..schemas.recommendation_enums import RecommendationType, RecommendationStatus


class ConfigurationRecommendationCreate(BaseModel):
    target_entity_type: str = Field(..., description="Tipo de entidad objetivo")
    target_entity_id: Optional[str] = Field(
        default=None, description="ID de la entidad objetivo"
    )
    proposed_change: str = Field(..., description="Cambio propuesto")
    recommendation_type: RecommendationType = Field(
        ..., description="Tipo de recomendación"
    )
    supporting_metrics: SupportingMetricsSchema = Field(
        ..., description="Métricas de apoyo"
    )
    historic_trace: HistoricTraceSchema = Field(
        ..., description="Rastro histórico"
    )
    recommendation_confidence: float = Field(
        ge=0.0, le=1.0, description="Nivel de confianza"
    )
    event_ids: Optional[List[str]] = Field(
        default=None, description="IDs de eventos asociados"
    )
    km_version_analyzed: Optional[UUID] = Field(
        default=None, description="Versión del knowledge model analizada"
    )
    algorithm_version: Optional[str] = Field(
        default=None, description="Versión del algoritmo"
    )


class ConfigurationRecommendationResponse(BaseModel):
    id: UUID = Field(..., description="ID de la recomendación")
    target_entity_type: str = Field(..., description="Tipo de entidad objetivo")
    target_entity_id: Optional[str] = Field(
        default=None, description="ID de la entidad objetivo"
    )
    proposed_change: str = Field(..., description="Cambio propuesto")
    recommendation_type: RecommendationType = Field(
        ..., description="Tipo de recomendación"
    )
    supporting_metrics: SupportingMetricsSchema = Field(
        ..., description="Métricas de apoyo"
    )
    historic_trace: HistoricTraceSchema = Field(
        ..., description="Rastro histórico"
    )
    recommendation_confidence: float = Field(
        ge=0.0, le=1.0, description="Nivel de confianza"
    )
    status: RecommendationStatus = Field(
        ..., description="Estado de la recomendación"
    )
    generated_at: datetime = Field(..., description="Fecha de generación")
    km_version_analyzed: Optional[UUID] = Field(
        default=None, description="Versión del knowledge model analizada"
    )
    algorithm_version: Optional[str] = Field(
        default=None, description="Versión del algoritmo"
    )
    event_ids: Optional[List[str]] = Field(
        default=None, description="IDs de eventos asociados"
    )
    resolved_by: Optional[str] = Field(
        default=None, description="Quién resolvió"
    )
    resolved_at: Optional[datetime] = Field(
        default=None, description="Cuándo fue resuelta"
    )
    resolution_justification: Optional[str] = Field(
        default=None, description="Justificación de la resolución"
    )

    model_config = ConfigDict(from_attributes=True)


class ResolveRecommendationRequest(BaseModel):
    approved: bool = Field(..., description="True para aprobar, False para rechazar")
    operator_id: str = Field(..., description="ID del operador")
    justification: Optional[str] = Field(
        default=None, description="Justificación de la decisión"
    )