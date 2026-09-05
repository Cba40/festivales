from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class AttendanceLevelModel(Base):
    __tablename__ = "attendance_levels"

    # Root chain / P2 chain schema: String(36) IDs
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    min_people: Mapped[int] = mapped_column(Integer, nullable=False)
    max_people: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # global_multiplier was dropped in f7a1c9d0e1b2 (P7) - not in current root chain state
    # global_multiplier: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("min_people >= 0", name="ck_attendance_levels_min_people_non_negative"),
        UniqueConstraint("event_id", "name", name="uq_attendance_level_event_name"),
        UniqueConstraint("event_id", "min_people", "max_people", name="uq_attendance_level_range"),
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())