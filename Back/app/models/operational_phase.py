"""OperationalPhase: Contexto operativo del territorio."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OperationalPhase(Base):
    """Representa el contexto operativo del territorio.

    No representa el estado del evento ni una decision.
    Se obtiene mediante un lookup determinista.
    """
    __tablename__ = "operational_phases"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    operational_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("operational_profiles.id", ondelete="CASCADE"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_min: Mapped[int] = mapped_column(Integer, nullable=False)
    end_min: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    profile: Mapped["OperationalProfile"] = relationship(back_populates="phases")
    zone_behaviors: Mapped[list["ZoneBehavior"]] = relationship(
        back_populates="phase", cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("operational_profile_id", "sort_order", name="uq_phase_profile_sort_order"),
        CheckConstraint("start_min >= 0", name="ck_phase_start_min_ge_0"),
        CheckConstraint("end_min > start_min", name="ck_phase_end_min_gt_start"),
        CheckConstraint("sort_order >= 0", name="ck_phase_sort_order_ge_0"),
    )
