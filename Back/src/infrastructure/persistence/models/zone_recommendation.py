from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class ZoneRecommendationModel(Base):
    __tablename__ = "zone_recommendations"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_day_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("event_days.id"),
        nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    zone_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("zones.id"),
        nullable=False,
    )
    recommendation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[float] = mapped_column(nullable=False)
    ranking: Mapped[int] = mapped_column(nullable=False)
    reasoning: Mapped[list] = mapped_column(JSONB, nullable=False)
    is_nearest: Mapped[bool] = mapped_column(nullable=False, default=False)
    metadata_json: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "score >= 0.0 AND score <= 1.0",
            name="ck_zone_recommendations_score_range",
        ),
    )