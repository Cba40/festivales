from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base


class ZoneBehaviorModel(Base):
    __tablename__ = "zone_behaviors"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    operational_phase_id: Mapped[UUID] = mapped_column(ForeignKey("operational_phases.id", ondelete="CASCADE"), nullable=False)
    # zone_types.id es VARCHAR(36) en la cadena raíz
    zone_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("zone_types.id", ondelete="CASCADE"), nullable=False)
    
    # Columnas originales de d0e1f2a3b4c5
    saturation_factor: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, server_default="1.0")
    availability_factor: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, server_default="1.0")
    resource_factor: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, server_default="1.0")
    priority_weight: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, server_default="1.0")
    
    # Columnas agregadas en f0e1d2c3b4a5
    density_factor: Mapped[float] = mapped_column(nullable=False, server_default="0.5")
    flow_restriction: Mapped[str] = mapped_column(String(20), nullable=False, server_default="OPEN")
    
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("operational_phase_id", "zone_type_id", name="uq_zb_phase_zone_type"),
        CheckConstraint("density_factor >= 0.0 AND density_factor <= 1.0", name="ck_zb_density_factor_range"),
        CheckConstraint("flow_restriction IN ('OPEN', 'REGULATED', 'CLOSED')", name="ck_zb_flow_restriction"),
    )

    operational_phase: Mapped["OperationalPhaseModel"] = relationship(back_populates="zone_behaviors")
    zone_type: Mapped["ZoneTypeModel"] = relationship(back_populates="zone_behaviors")
