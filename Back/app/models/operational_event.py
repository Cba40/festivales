"""OperationalEvent: Hechos reales ocurridos durante una jornada."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OperationalEvent(Base):
    """Representa hechos reales ocurridos durante una jornada.

    Pertenece al EventDay. No pertenece al OperationalProfile.
    Su funcion consiste unicamente en alterar temporalmente el comportamiento esperado.
    """
    __tablename__ = "operational_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_day_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("event_days.id", ondelete="CASCADE"), nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    start_min: Mapped[int] = mapped_column(Integer, nullable=False)
    end_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    event_day: Mapped["EventDay"] = relationship(back_populates="operational_events")

    __table_args__ = (
        Index("ix_oe_event_day_active", "event_day_id", "is_active", postgresql_where=text("is_active = true")),
        CheckConstraint("start_min >= 0", name="ck_oe_start_min_ge_0"),
        CheckConstraint("end_min IS NULL OR end_min > start_min", name="ck_oe_end_min_gt_start"),
    )
