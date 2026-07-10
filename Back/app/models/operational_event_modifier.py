"""OperationalEventModifier: Configuración de cómo un evento altera factores de comportamiento."""
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OperationalEventModifier(Base):
    """Define como un OperationalEvent altera los factores de comportamiento de un ZoneType.

    Almacena multiplicadores configurables por tipo de evento y tipo de zona.
    zone_type_id = NULL significa que aplica a todos los tipos de zona.
    """
    __tablename__ = "operational_event_modifiers"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    zone_type_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("zone_types.id", ondelete="SET NULL"), nullable=True,
    )
    saturation_multiplier: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, server_default=text("1.0"))
    availability_multiplier: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, server_default=text("1.0"))
    priority_modifier: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, server_default=text("0.0"))

    zone_type: Mapped[Optional["ZoneType"]] = relationship()

    __table_args__ = (
        UniqueConstraint("event_type", "zone_type_id", name="uq_oem_event_type_zone_type"),
    )
