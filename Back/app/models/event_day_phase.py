"""EventDayPhase: Fase materializada de una jornada operativa."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EventDayPhase(Base):
    """Representa la materializacion de una fase operativa en una jornada.

    Es propiedad exclusiva de un EventDay (composicion interna).
    Referencia a OperationalPhase para mantener trazabilidad con el perfil.
    """
    __tablename__ = "event_day_phases"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_day_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("event_days.id", ondelete="CASCADE"), nullable=False,
    )
    operational_phase_id: Mapped[UUID] = mapped_column(
        ForeignKey("operational_phases.id"), nullable=False,
    )
    start_min: Mapped[int] = mapped_column(Integer, nullable=False)
    end_min: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    event_day: Mapped["EventDay"] = relationship(back_populates="phases")
    operational_phase: Mapped["OperationalPhase"] = relationship()

    __table_args__ = (
        CheckConstraint("start_min >= 0", name="ck_edp_start_min_non_negative"),
        CheckConstraint("end_min > start_min", name="ck_edp_end_min_gt_start_min"),
    )
