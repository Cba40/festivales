from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base


class OperationalEventModel(Base):
    __tablename__ = "operational_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    target_zone_id: Mapped[UUID] = mapped_column(ForeignKey("zones.id"), nullable=False)
    impact_value: Mapped[int] = mapped_column(nullable=False)
    is_incident: Mapped[bool] = mapped_column(nullable=False)
    start_timestamp: Mapped[datetime] = mapped_column(nullable=False)
    end_timestamp: Mapped[datetime] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    target_zone: Mapped["ZoneModel"] = relationship(back_populates="operational_events")
