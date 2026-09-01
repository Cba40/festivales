"""OperationalEvent: Hechos reales ocurridos durante una jornada."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

EVENT_TYPES = [
    "accidente",
    "corte_energia",
    "evacuacion",
    "incendio",
    "congestion_extraordinaria",
    "escenario_finalizado",
    "apertura_extraordinaria",
    "corte_calle",
    "fin_espectaculo",
    "tormenta",
    "incidente_operativo",
]

EFFECT_TYPES = [
    "reduccion_capacidad",
    "cierre_total",
    "aumento_demanda",
    "incidente_sin_impacto",
]


class OperationalEvent(Base):
    """Representa hechos reales ocurridos durante una jornada.

    Pertenece al EventDay. No pertenece al OperationalProfile.
    Su funcion consiste unicamente en alterar temporalmente el comportamiento esperado.
    """
    __tablename__ = "operational_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_day_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("event_days.id", ondelete="CASCADE"), nullable=False,
    )
    zone_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("zones.id"), nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    effect_type: Mapped[str] = mapped_column(String(30), nullable=False)
    effect_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_incident: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false"),
    )
    start_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 8), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(11, 8), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    event_day: Mapped["EventDay"] = relationship(back_populates="operational_events")
    zone: Mapped["Zone"] = relationship()

    __table_args__ = (
        CheckConstraint("end_timestamp > start_timestamp", name="ck_operational_events_temporal"),
        CheckConstraint(
            "(effect_type = 'reduccion_capacidad' AND effect_value IS NOT NULL AND effect_value BETWEEN 1 AND 100) OR "
            "(effect_type = 'cierre_total' AND effect_value IS NULL) OR "
            "(effect_type = 'aumento_demanda' AND effect_value IS NOT NULL AND effect_value >= 1) OR "
            "(effect_type = 'incidente_sin_impacto' AND effect_value IS NULL)",
            name="ck_operational_events_effect_value",
        ),
        CheckConstraint(
            "latitude IS NULL OR (latitude BETWEEN -90 AND 90)",
            name="ck_operational_events_latitude",
        ),
        CheckConstraint(
            "longitude IS NULL OR (longitude BETWEEN -180 AND 180)",
            name="ck_operational_events_longitude",
        ),
        Index("ix_operational_events_event_day_id", "event_day_id"),
        Index("ix_operational_events_zone_id", "zone_id"),
        Index(
            "ix_operational_events_active_window",
            "is_active", "start_timestamp", "end_timestamp",
            postgresql_where=text("is_active = true"),
        ),
    )
