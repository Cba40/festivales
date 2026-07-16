from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class AttendanceLevelModel(Base):
    __tablename__ = "attendance_levels"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    multiplier: Mapped[float] = mapped_column(nullable=False)

    __table_args__ = (
        CheckConstraint("multiplier >= 0.1 AND multiplier <= 2.0", name="ck_attendance_levels_multiplier_range"),
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
