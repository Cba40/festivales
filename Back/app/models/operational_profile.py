"""OperationalProfile: Patron operativo esperado de una jornada."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OperationalProfile(Base):
    """Describe el patron operativo esperado de una jornada.

    No representa un dia de la semana, ni un calendario, ni un espectaculo.
    Representa unicamente un patron operativo territorial.
    """
    __tablename__ = "operational_profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    phases: Mapped[list["OperationalPhase"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan",
    )
