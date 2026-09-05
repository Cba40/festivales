"""OperationalObservation: Registro de densidad observada en zona durante una jornada."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OperationalObservation(Base):
    """Representa una observación de densidad real en una zona durante un día de evento."""
    __tablename__ = "operational_observations"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_day_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("event_days.id"), nullable=False,
    )
    zone_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("zones.id"), nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_density: Mapped[int] = mapped_column(Integer, nullable=False)
    observer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, server_default=text("'manual'"))
    meta: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    event_day: Mapped["EventDay"] = relationship(back_populates="operational_observations")
    zone: Mapped["Zone"] = relationship()

    __table_args__ = (
        CheckConstraint("observed_density >= 0", name="ck_operational_observations_density_non_negative"),
        Index("ix_operational_observations_event_day_id", "event_day_id"),
        Index("ix_operational_observations_zone_id", "zone_id"),
        Index("ix_operational_observations_timestamp", "timestamp"),
    )