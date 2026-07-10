"""ZoneBehavior: Comportamiento esperado de un ZoneType durante una OperationalPhase."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ZoneBehavior(Base):
    """Representa el comportamiento esperado de un ZoneType durante una OperationalPhase.

    Definido por la combinacion de OperationalPhase y ZoneType.
    Contiene unicamente factores de comportamiento. No representa una respuesta puntual.
    """
    __tablename__ = "zone_behaviors"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    operational_phase_id: Mapped[UUID] = mapped_column(
        ForeignKey("operational_phases.id", ondelete="CASCADE"), nullable=False,
    )
    zone_type_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("zone_types.id", ondelete="CASCADE"), nullable=False,
    )
    saturation_factor: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, server_default=text("1.0"))
    availability_factor: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, server_default=text("1.0"))
    resource_factor: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, server_default=text("1.0"))
    priority_weight: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, server_default=text("1.0"))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    phase: Mapped["OperationalPhase"] = relationship(back_populates="zone_behaviors")
    zone_type: Mapped["ZoneType"] = relationship()

    __table_args__ = (
        UniqueConstraint("operational_phase_id", "zone_type_id", name="uq_zb_phase_zone_type"),
        CheckConstraint("saturation_factor > 0", name="ck_zb_saturation_gt_0"),
        CheckConstraint("availability_factor > 0", name="ck_zb_availability_gt_0"),
        CheckConstraint("resource_factor > 0", name="ck_zb_resource_gt_0"),
        CheckConstraint("priority_weight > 0", name="ck_zb_priority_gt_0"),
    )
