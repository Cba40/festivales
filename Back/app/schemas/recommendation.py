"""Pydantic response DTOs for the recommendations endpoint."""
from pydantic import BaseModel, Field


class ZoneRecommendationItem(BaseModel):
    zone_id: str
    score: float = Field(ge=0.0, le=1.0)
    reasoning: list[str]


class RecommendationResponse(BaseModel):
    event_id: str
    timestamp: str
    recommendations: list[ZoneRecommendationItem]
