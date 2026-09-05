from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base


class OperationalObservationModel(Base):
    __tablename__ = "operational_observations"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_day_id: Mapped[str] = mapped_column(String(36), ForeignKey("event_days.id"), nullable=False)
    zone_id: Mapped[str] = mapped_column(String(36), ForeignKey("zones.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    observed_density: Mapped[int] = mapped_column(nullable=False)
    observer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    meta: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint("observed_density >= 0", name="ck_operational_observations_density_non_negative"),
    )

    event_day: Mapped["EventDayModel"] = relationship(back_populates="operational_observations")
    zone: Mapped["ZoneModel"] = relationship()