from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base


class OperationalPhaseModel(Base):
    __tablename__ = "operational_phases"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    operational_profile_id: Mapped[UUID] = mapped_column(ForeignKey("operational_profiles.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    sequence_order: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        UniqueConstraint("operational_profile_id", "sequence_order"),
        CheckConstraint("sequence_order > 0", name="ck_operational_phases_sequence_order_positive"),
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    profile: Mapped["OperationalProfileModel"] = relationship(back_populates="phases")
    zone_behaviors: Mapped[list["ZoneBehaviorModel"]] = relationship(back_populates="operational_phase")
    event_day_phases: Mapped[list["EventDayPhaseModel"]] = relationship(back_populates="operational_phase")
