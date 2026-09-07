from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Integer, JSON, func, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class OperationalObservationModel(Base):
    __tablename__ = "operational_observations"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_day_id: Mapped[str] = mapped_column(String(36), nullable=False)
    zone_id: Mapped[str] = mapped_column(String(36), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(nullable=False)
    observed_density: Mapped[int] = mapped_column(Integer, nullable=False)
    observer_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, server_default="manual")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())