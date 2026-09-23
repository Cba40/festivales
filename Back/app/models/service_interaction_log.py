"""ServiceInteractionLog: log anónimo de consultas a servicios municipales.

Registro APPEND-ONLY, una fila por request efectivo a un endpoint de producto
(recomendación/gastronomía/sanitarios/hidratación/descanso/transporte/salida/
alojamiento/emergencia). Sin datos personales: no se persiste ip, device,
coordenadas, user_id, session, current_zone_id ni event_day_id.

El ``event_id`` se guarda tal cual lo recibe el handler (sin FK: en entornos
de prueba el frontend puede enviar un id sintético que no existe en ``events``).
``zone_ids`` contiene las zonas DEVUELTAS por el servicio (no la zona actual
del usuario). ``result_status`` sigue la clasificación cerrada del informe:
ok | empty | unavailable | error.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

SERVICE_CATEGORIES = [
    "parking",
    "gastronomy",
    "bathroom",
    "hydration",
    "rest",
    "transport",
    "exit",
    "accommodation",
    "emergency",
]

RESULT_STATUSES = [
    "ok",
    "empty",
    "unavailable",
    "error",
]


class ServiceInteractionLog(Base):
    """Interacción digital anónima con un servicio municipal a nivel request."""
    __tablename__ = "service_interaction_log"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_id: Mapped[str] = mapped_column(String(36), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    service_category: Mapped[str] = mapped_column(String(50), nullable=False)
    result_status: Mapped[str] = mapped_column(String(12), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    request_mode: Mapped[str | None] = mapped_column(String(50), nullable=True)
    zone_ids: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    __table_args__ = (
        Index("ix_service_interaction_event_category_time", "event_id", "service_category", "timestamp"),
        Index("ix_service_interaction_timestamp", "timestamp"),
        Index("ix_service_interaction_result_status", "result_status"),
    )