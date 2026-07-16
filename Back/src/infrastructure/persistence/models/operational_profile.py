from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base


class OperationalProfileModel(Base):
    __tablename__ = "operational_profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    event_days: Mapped[list["EventDayModel"]] = relationship(back_populates="operational_profile")
    phases: Mapped[list["OperationalPhaseModel"]] = relationship(back_populates="profile")
