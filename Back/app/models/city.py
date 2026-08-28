"""City: ciudades / localidades territoriales (Emergencia V1 - S1).

Modelo territorial compartido: los puntos de infraestructura (incluida la
emergencia) pertenecen a una ciudad, no a un evento. Sigue el patrón de
Hospedaje V1 (entidad propia + sin ``event_id``).
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class City(Base):
    """Ciudad / localidad territorial.

    Tabla ``cities``.

    La unicidad se define sobre la tripleta (``name``, ``province``, ``country``).
    Los campos ``created_at`` / ``updated_at`` siguen la convención del repo.
    """
    __tablename__ = "cities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    province: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="Argentina")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False,
    )

    emergencies: Mapped[List["Emergency"]] = relationship(
        back_populates="city",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint("name", "province", "country", name="uq_cities_name_province_country"),
    )
