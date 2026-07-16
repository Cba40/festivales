from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base


class EventDayModel(Base):
    __tablename__ = "event_days"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_date: Mapped[date] = mapped_column(nullable=False)
    operational_profile_id: Mapped[UUID] = mapped_column(ForeignKey("operational_profiles.id"), nullable=False)
    attendance_level_id: Mapped[UUID] = mapped_column(ForeignKey("attendance_levels.id"), nullable=False)
    operational_start_min: Mapped[int] = mapped_column(nullable=False)
    operational_end_min: Mapped[int] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    operational_profile: Mapped["OperationalProfileModel"] = relationship(back_populates="event_days")
    attendance_level: Mapped["AttendanceLevelModel"] = relationship()
    phases: Mapped[list["EventDayPhaseModel"]] = relationship(back_populates="event_day")
