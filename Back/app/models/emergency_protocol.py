"""EmergencyProtocol: protocolos de emergencia (Emergencia V2 - Fase S1).

Catálogo de protocolos por contexto (``festival`` / ``transporte`` /
``hospedaje``). Cada protocolo tiene un título único dentro de su contexto
(``UNIQUE(context, title)``), una lista de pasos accionables en JSONB y una
prioridad restringida a 1-3.

``target_type`` reutiliza el enum canónico ``EmergencyType`` de V1 y es
opcional: aplica el protocolo a un tipo de emergencia específico o lo deja
genérico (``None``). ``order`` permite ordenar los protocolos de un contexto
(no negativo, ``CHECK(order >= 0)``).
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum as SAEnum, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.emergency import EmergencyType


class EmergencyProtocolContext(str, Enum):
    """Contextos en los que se aplica un protocolo de emergencia."""
    FESTIVAL = "festival"
    TRANSPORTE = "transporte"
    HOSPEDAJE = "hospedaje"


class EmergencyProtocol(Base):
    """Protocolo de emergencia accionable para un contexto.

    Tabla ``emergency_protocols``.

    ``steps`` es un JSONB con una lista de instrucciones simples en orden de
    ejecución. La unicidad (context, title) garantiza que el mismo título no
    se repita dentro de un contexto. Los timestamps siguen la convención del repo.
    """
    __tablename__ = "emergency_protocols"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    context: Mapped[EmergencyProtocolContext] = mapped_column(
        SAEnum(EmergencyProtocolContext, name="emergency_protocol_context", length=32, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    icon: Mapped[str] = mapped_column(String(10), nullable=False)
    steps: Mapped[list[str]] = mapped_column(JSONB().with_variant(JSON, "sqlite"), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    target_type: Mapped[Optional[EmergencyType]] = mapped_column(
        SAEnum(EmergencyType, name="emergency_type", length=32, values_callable=lambda e: [m.value for m in e], validate_strings=True),
        nullable=True,
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("context", "title", name="uq_emergency_protocols_context_title"),
        CheckConstraint("priority IN (1, 2, 3)", name="ck_emergency_protocols_priority"),
        CheckConstraint('"order" >= 0', name="ck_emergency_protocols_order"),
    )