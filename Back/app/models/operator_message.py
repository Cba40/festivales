"""OperatorMessage: Mensaje programable del operador para el público (RFC-ALERTS-MESSAGES-V1)."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
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

MESSAGE_STATUSES = [
    "draft",
    "published",
    "cancelled",
]

MESSAGE_PRIORITIES = [
    "normal",
    "high",
    "urgent",
]


class OperatorMessage(Base):
    """Mensaje programable del operador municipal dirigido al público.

    Se define previamente (status=draft) y se publica cuando corresponde
    (status=published). El endpoint público sólo expone mensajes publicados
    dentro de la ventana publish_at <= now < expires_at (si expires_at no es NULL).
    """
    __tablename__ = "operator_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False,
    )
    line_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("transport_lines.id", ondelete="SET NULL"), nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'draft'"),
    )
    priority: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default=text("'normal'"),
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    publish_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'cancelled')",
            name="check_message_status",
        ),
        CheckConstraint(
            "priority IN ('normal', 'high', 'urgent')",
            name="check_message_priority",
        ),
        CheckConstraint(
            "expires_at IS NULL OR expires_at > publish_at",
            name="check_message_temporal",
        ),
        Index(
            "ix_messages_published_window",
            "status", "publish_at", "expires_at",
            postgresql_where=text("status = 'published'"),
        ),
    )