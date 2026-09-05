from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String, Text, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base


class EventDayModel(Base):
    __tablename__ = "event_days"

    # Root chain schema: String(36) IDs, legacy columns
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id"), nullable=False)
    date: Mapped[date] = mapped_column(nullable=False)
    day_of_week: Mapped[str] = mapped_column(String(10), nullable=False)
    weather: Mapped[str | None] = mapped_column(String(20), nullable=True)
    headliner_artist: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_attendance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peak_hour_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peak_hour_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opening_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closing_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    operational_profile_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # FK to operational_profiles if exists
    attendance_level_id: Mapped[str] = mapped_column(String(36), ForeignKey("attendance_levels.id"), nullable=False)
    estimated_vehicles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    average_parking_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    operational_start_min: Mapped[int] = mapped_column(nullable=False)
    operational_end_min: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        CheckConstraint("operational_start_min >= 0", name="ck_event_days_operational_start_min_non_negative"),
        CheckConstraint("operational_end_min > operational_start_min", name="ck_event_days_operational_end_min_gt_start"),
        UniqueConstraint("event_id", "date", name="uq_event_day_event_date"),
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # Relationships - tables that exist in root chain
    # operational_profile: Mapped["OperationalProfileModel"] = relationship(back_populates="event_days")  # Table doesn't exist in root chain
    # attendance_level: Mapped["AttendanceLevelModel"] = relationship()  # Table doesn't exist in root chain
    phases: Mapped[list["EventDayPhaseModel"]] = relationship(back_populates="event_day")  # Table EXISTS in root chain (e5f6a7b8c9d0)
    # operational_observations: Mapped[list["OperationalObservationModel"]] = relationship(back_populates="event_day")  # Added in this iteration
