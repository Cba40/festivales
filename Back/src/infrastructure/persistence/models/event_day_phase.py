from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base


class EventDayPhaseModel(Base):
    __tablename__ = "event_day_phases"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    # event_days.id es VARCHAR(36) en la cadena raíz
    event_day_id: Mapped[str] = mapped_column(String(36), ForeignKey("event_days.id", ondelete="CASCADE"), nullable=False)
    operational_phase_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("operational_phases.id"), nullable=False)
    start_min: Mapped[int] = mapped_column(nullable=False)
    end_min: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        CheckConstraint("start_min >= 0", name="ck_edp_start_min_non_negative"),
        CheckConstraint("end_min > start_min", name="ck_edp_end_min_gt_start_min"),
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    event_day: Mapped["EventDayModel"] = relationship(back_populates="phases")
    operational_phase: Mapped["OperationalPhaseModel"] = relationship(back_populates="event_day_phases")
