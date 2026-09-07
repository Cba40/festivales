from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class HistoricTraceSchema(BaseModel):
    prediction_ids: List[str] = Field(
        default_factory=list, description="IDs de predicciones asociadas"
    )
    observation_ids: List[str] = Field(
        default_factory=list, description="IDs de observaciones asociadas"
    )
    operational_event_ids: List[str] = Field(
        default_factory=list, description="IDs de eventos operativos asociados"
    )