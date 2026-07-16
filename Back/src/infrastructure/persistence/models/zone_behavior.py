from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.domain.entities.zone_behavior import FlowRestriction
from src.infrastructure.db.base import Base


class ZoneBehaviorModel(Base):
    __tablename__ = "zone_behaviors"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    operational_phase_id: Mapped[UUID] = mapped_column(ForeignKey("operational_phases.id"), nullable=False)
    zone_type_id: Mapped[UUID] = mapped_column(ForeignKey("zone_types.id"), nullable=False)
    density_factor: Mapped[float] = mapped_column(nullable=False)
    flow_restriction: Mapped[FlowRestriction] = mapped_column(SAEnum(FlowRestriction), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("operational_phase_id", "zone_type_id"),
        CheckConstraint("density_factor >= 0.0 AND density_factor <= 1.0", name="ck_zone_behaviors_density_factor_range"),
    )

    operational_phase: Mapped["OperationalPhaseModel"] = relationship(back_populates="zone_behaviors")
    zone_type: Mapped["ZoneTypeModel"] = relationship(back_populates="zone_behaviors")
