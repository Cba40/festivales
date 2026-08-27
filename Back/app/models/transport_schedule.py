"""TransportSchedule: Horarios específicos de transporte público (S1 Transporte V1)."""
import uuid

from sqlalchemy import ForeignKey, Index, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class TransportSchedule(Base):
    """Tabla de horarios de transporte público.

    Tabla ``transport_schedules`` (migración d5e6f7a8b9c0).

    Cada registro representa un servicio concreto: un horario de salida
    en una parada específica de una línea, con un destino determinado.
    Los horarios son específicos (no frecuencias calculadas).
    """
    __tablename__ = "transport_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    line_stop_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("transport_line_stops.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_type: Mapped[str] = mapped_column(String(20), nullable=False)
    departure_time = mapped_column(Time, nullable=False)
    destination: Mapped[str] = mapped_column(String(100), nullable=False)

    __table_args__ = (
        UniqueConstraint("line_stop_id", "day_type", "departure_time", "destination",
                         name="uq_transport_schedules_line_stop_schedule"),
        Index("idx_ts_line_stop", "line_stop_id"),
        Index("idx_ts_day_type", "day_type"),
    )

    line_stop: Mapped["TransportLineStop"] = relationship(
        "TransportLineStop", back_populates="schedules",
    )
