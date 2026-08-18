"""ServiceConfig: Configuración de permanencias de servicios para personas."""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ServiceConfig(Base):
    """Configuración de permanencias de servicios (SERVICIOS_PERSONAS_DISENO.md §3/§7).

    Tabla `service_configs` (migración d4e5f6a7b8c9):

    - Un solo default global por (zone_type_id, subtipo): event_day_id NULL.
    - Un solo override por jornada por (zone_type_id, subtipo, event_day_id).
    - `average_duration_min` se almacena en MINUTOS; la conversión a horas es
      responsabilidad del modelo (BathroomV1Model.duration_hours).

    Sin lógica de negocio: solo mapeo de la tabla ya existente.
    """
    __tablename__ = "service_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    zone_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("zone_types.id"), nullable=False)
    subtipo: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    event_day_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("event_days.id"), nullable=True)
    average_duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index(
            "uq_service_config_default",
            "zone_type_id",
            text("COALESCE(subtipo, '')"),
            unique=True,
            postgresql_where=text("event_day_id IS NULL"),
        ),
        Index(
            "uq_service_config_override",
            "zone_type_id",
            text("COALESCE(subtipo, '')"),
            "event_day_id",
            unique=True,
            postgresql_where=text("event_day_id IS NOT NULL"),
        ),
    )