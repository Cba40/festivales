"""Accommodation: alojamientos de hospedaje (Hospedaje V1, S1).

Modelo dedicado y determinístico del módulo de Hospedaje. Reemplaza el uso
genérico de ``zones.type='hospedaje'`` por una entidad propia, siguiendo el
mismo patrón de Transporte V2 (tabla dedicada + adapter + endpoint de producto).
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, Float, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AccommodationType(Enum):
    """Tipos canónicos de alojamiento. No se permiten strings libres."""
    HOTEL = "hotel"
    HOSTEL = "hostel"
    CAMPING = "camping"
    OTHER = "other"


class Accommodation(Base):
    """Alojamiento asociado a un evento.

    Tabla ``accommodations`` (migración generada en S1).

    Cada alojamiento tiene un nombre único dentro del evento y un tipo
    canónico (``AccommodationType``). Los campos ``created_at`` / ``updated_at``
    siguen la convención del repo.
    """
    __tablename__ = "accommodations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[AccommodationType] = mapped_column(
        SAEnum(AccommodationType, name="accommodation_type", length=32, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    official_info_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("event_id", "name", name="uq_accommodations_event_name"),
        Index("idx_accommodations_event", "event_id"),
    )
