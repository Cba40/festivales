"""Emergency: puntos de emergencia de una ciudad (Emergencia V1 - S1).

Entidad dedicada y determinística del módulo de Emergencia. Reemplaza el uso
genérico de ``zones.type='emergencia'`` por una entidad propia asociada a una
ciudad (patrón de Hospedaje V1, sin ``event_id``).

``latitude`` / ``longitude`` son opcionales (nullable) para soportar números de
emergencia sin ubicación física (911, 107, 100). La obligatoriedad según tipo se
valida a nivel de aplicación, no de base de datos.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EmergencyType(str, Enum):
    """Tipos canónicos de emergencia (valores en español, coherentes con el sistema)."""
    policia = "policia"
    bomberos = "bomberos"
    salud = "salud"
    defensa_civil = "defensa_civil"
    numero_emergencia = "numero_emergencia"  # 911, 107, 100 sin ubicación física
    otro = "otro"


class Emergency(Base):
    """Punto de emergencia asociado a una ciudad.

    Tabla ``emergencies``.

    Cada emergencia tiene un nombre único dentro de la ciudad y un tipo canónico
    (``EmergencyType``). Los campos ``created_at`` / ``updated_at`` siguen la
    convención del repo.
    """
    __tablename__ = "emergencies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    city_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("cities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[EmergencyType] = mapped_column(
        SAEnum(EmergencyType, name="emergency_type", length=32, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    emergency_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    services: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    schedule: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    city: Mapped["City"] = relationship(back_populates="emergencies")

    __table_args__ = (
        UniqueConstraint("city_id", "name", name="uq_emergencies_city_name"),
        Index("idx_emergencies_city", "city_id"),
    )
