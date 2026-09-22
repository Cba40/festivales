"""TransportAlert: Alerta operativa inmediata dirigida al público (RFC-ALERTS-MESSAGES-V1)."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

ALERT_TYPES = [
    "info",
    "warning",
    "disruption",
    "closure",
]


class TransportAlert(Base):
    """Alerta operativa de carácter inmediato mostrada al público.

    Se activa dentro de una ventana temporal (valid_from / valid_until) y se
    desactiva con is_active. line_id es opcional; si se define, la alerta se
    refiere a una línea puntual de transporte del evento.
    """
    __tablename__ = "transport_alerts"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False,
    )
    line_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("transport_lines.id", ondelete="SET NULL"), nullable=True,
    )
    alert_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "alert_type IN ('info', 'warning', 'disruption', 'closure')",
            name="check_alert_type",
        ),
        CheckConstraint("valid_until > valid_from", name="check_alert_temporal"),
        Index(
            "ix_alerts_active_window",
            "is_active", "valid_from", "valid_until",
            postgresql_where=text("is_active = true"),
        ),
    )