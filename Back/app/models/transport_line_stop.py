"""TransportLineStop: Relación N:N entre líneas de transporte y paradas (S1 Transporte V1)."""
import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TransportLineStop(Base):
    """Tabla de asociación entre TransportLine y Zone (paradas de transporte).

    Tabla ``transport_line_stops`` (migración b2c3d4e5f6a7).

    Cada registro indica que una parada (Zone con type='transporte')
    pertenece a una línea de transporte, con un ``stop_order`` que define
    el orden en el recorrido.
    """
    __tablename__ = "transport_line_stops"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    line_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transport_lines.id", ondelete="CASCADE"),
        nullable=False,
    )
    zone_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("zones.id", ondelete="CASCADE"),
        nullable=False,
    )
    stop_order: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("line_id", "zone_id", name="uq_transport_line_stops_line_zone"),
        UniqueConstraint("line_id", "stop_order", name="uq_transport_line_stops_line_order"),
        Index("idx_tls_line", "line_id"),
        Index("idx_tls_zone", "zone_id"),
    )

    line: Mapped["TransportLine"] = relationship("TransportLine", back_populates="stops")
    zone: Mapped["Zone"] = relationship("Zone", back_populates="transport_line_stops")
    schedules: Mapped[list["TransportSchedule"]] = relationship(
        "TransportSchedule", back_populates="line_stop",
        order_by="TransportSchedule.departure_time",
    )
