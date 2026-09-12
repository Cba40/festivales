from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

MetricStatus = Literal["ENABLED", "LIMITED", "BLOCKED"]
AnomalySeverity = Literal["high", "medium", "low"]


class MetricResultResponse(BaseModel):
    name: str = Field(..., description="Identificador de la métrica")
    display_name: str = Field(..., description="Nombre legible de la métrica")
    status: MetricStatus = Field(..., description="ENABLED | LIMITED | BLOCKED")
    value: float | None = Field(None, description="Valor calculado (None si no aplica)")
    reason: str = Field(..., description="Razón del estado")
    data_points: int = Field(..., description="Número de puntos de dato utilizados")
    limitations: List[str] = Field(
        default_factory=list, description="Limitaciones documentadas de la métrica"
    )
    is_provisional: bool = Field(
        True, description="Indica si la fórmula/umbral es provisional (Etapa 2)"
    )


class EvaluationRequest(BaseModel):
    event_day_id: str = Field(..., description="ID del event_day a evaluar")
    phase_id: str = Field(..., description="ID de la fase operativa a evaluar")


class AnomalyResponse(BaseModel):
    metric_name: str = Field(..., description="Métrica afectada")
    severity: AnomalySeverity = Field(..., description="Severidad: high | medium | low")
    description: str = Field(..., description="Descripción de la anomalía")
    suggested_action: str = Field(..., description="Acción sugerida")
    value: float | None = Field(None, description="Valor que disparó la anomalía")
    is_provisional: bool = Field(
        True, description="Anomalía basada en umbrales provisionales"
    )


class RecommendationCreatedResponse(BaseModel):
    id: str = Field(..., description="ID de la recomendación creada")
    status: str = Field(..., description="Estado de la recomendación creada")
    metric_name: str = Field(..., description="Métrica que originó la recomendación")


class EvaluationResponse(BaseModel):
    metrics: List[MetricResultResponse] = Field(
        ..., description="Resultado de las 4 métricas"
    )
    anomalies_detected: int = Field(..., description="Cantidad de anomalías detectadas")
    anomalies: List[AnomalyResponse] = Field(
        default_factory=list, description="Detalle de las anomalías detectadas"
    )
    recommendations_created: List[RecommendationCreatedResponse] = Field(
        default_factory=list, description="Recomendaciones creadas"
    )