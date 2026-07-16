from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base


class EventDayPhaseModel(Base):
    __tablename__ = "event_day_phases"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_day_id: Mapped[UUID] = mapped_column(ForeignKey("event_days.id"), nullable=False)
    operational_phase_id: Mapped[UUID] = mapped_column(ForeignKey("operational_phases.id"), nullable=False)
    start_min: Mapped[int] = mapped_column(nullable=False)
    end_min: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        CheckConstraint("start_min >= 0", name="ck_event_day_phases_start_min_non_negative"),
        CheckConstraint("end_min > start_min", name="ck_event_day_phases_end_min_gt_start_min"),
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    event_day: Mapped["EventDayModel"] = relationship(back_populates="phases")
    operational_phase: Mapped["OperationalPhaseModel"] = relationship(back_populates="event_day_phases")
