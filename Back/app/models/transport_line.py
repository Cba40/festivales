"""TransportLine: Línea de transporte público (S1 Transporte V1)."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class TransportLine(Base):
    """Línea de transporte público asociada a un evento.

    Tabla ``transport_lines`` (migración a1b2c3d4e5f6).

    Cada línea tiene un nombre único dentro del evento, un tipo (urbano /
    interurbano), la empresa operadora y opcionalmente un color hex para
    rendering en mapa.

    Campos ``created_at`` / ``updated_at`` siguen la convención del repo.
    """
    __tablename__ = "transport_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    company: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("event_id", "name", name="uq_transport_lines_event_name"),
        Index("idx_transport_lines_event", "event_id"),
    )
