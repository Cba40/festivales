from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class PredictionModel(Base):
    __tablename__ = "predictions"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    timestamp: Mapped[datetime] = mapped_column(nullable=False, unique=True)
    active_phase_id: Mapped[UUID] = mapped_column(nullable=False)
    active_event_day_phase_id: Mapped[UUID] = mapped_column(nullable=False)
    zone_states_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("timestamp", name="uq_predictions_timestamp"),
    )
