import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EventDay(Base):
    __tablename__ = "event_days"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    day_of_week: Mapped[str] = mapped_column(String(10), nullable=False)
    entry_start_min: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_peak_start_min: Mapped[int] = mapped_column(Integer, nullable=False)
    activity_peak_end_min: Mapped[int] = mapped_column(Integer, nullable=False)
    exit_start_min: Mapped[int] = mapped_column(Integer, nullable=False)
    event_end_min: Mapped[int] = mapped_column(Integer, nullable=False)
    weather: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    headliner_artist: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    estimated_attendance: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    event = relationship("Event", back_populates="event_days")
    event_day_zone_factors = relationship("EventDayZoneFactor", back_populates="event_day")
    state_overrides = relationship("StateOverride", back_populates="event_day")

    __table_args__ = (
        UniqueConstraint("event_id", "date", name="uq_event_day_event_date"),
        Index("ix_event_day_event_active", "event_id", "is_active", postgresql_where=text("is_active = true")),
        CheckConstraint(
            "entry_start_min < activity_peak_start_min AND "
            "activity_peak_start_min < activity_peak_end_min AND "
            "activity_peak_end_min < exit_start_min AND "
            "exit_start_min < event_end_min",
            name="ck_event_day_minute_order"
        ),
    )
