from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SupportingMetricsSchema(BaseModel):
    metric: str = Field(..., description="Nombre de la métrica")
    value: float = Field(..., description="Valor de la métrica")
    threshold: Optional[float] = Field(
        default=None, description="Umbral de comparación"
    )
    predicted: Optional[float] = Field(
        default=None, description="Valor predicho"
    )
    observed: Optional[float] = Field(
        default=None, description="Valor observado"
    )
    sample_count: Optional[int] = Field(
        default=None, description="Número de muestreos"
    )
    zone_id: Optional[str] = Field(
        default=None, description="ID de la zona asociada"
    )
    phase_id: Optional[str] = Field(
        default=None, description="ID de la fase asociada"
    )