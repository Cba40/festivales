# backend/app/models/configuration_recommendation.py

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import String, Text, Uuid, Integer, Boolean, DateTime, JSON, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ConfigurationRecommendation(Base):
    __tablename__ = "configuration_recommendations"

    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    target_entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_entity_id: Mapped[Optional[str]] = mapped_column(String(36))
    proposed_change: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    supporting_metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    historic_trace: Mapped[dict] = mapped_column(JSON, nullable=False)
    recommendation_confidence: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    km_version_analyzed: Mapped[Optional[UUID]] = mapped_column(Uuid)
    algorithm_version: Mapped[Optional[str]] = mapped_column(String(50))
    event_ids: Mapped[list] = mapped_column(JSON, nullable=False)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(100))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    resolution_justification: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self):
        return f"ConfigurationRecommendation(id={self.id})"