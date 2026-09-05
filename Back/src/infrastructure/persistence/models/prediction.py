from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import INTEGER, JSON, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class PredictionModel(Base):
    __tablename__ = "predictions"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    timestamp: Mapped[datetime] = mapped_column(nullable=False, unique=True)
    event_day_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("event_days.id"), nullable=False, index=True
    )
    knowledge_model_version_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("knowledge_model_versions.id"), nullable=True
    )
    active_phase_id: Mapped[UUID] = mapped_column(nullable=False)
    active_event_day_phase_id: Mapped[UUID] = mapped_column(nullable=False)
    zone_states_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("timestamp", name="uq_predictions_timestamp"),
    )
