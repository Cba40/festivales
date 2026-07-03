import uuid
from datetime import date, datetime

from sqlalchemy import String, Integer, Boolean, Date, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EventDay(Base):
    __tablename__ = "event_days"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    day_of_week: Mapped[str] = mapped_column(String(10), nullable=False)
    weather: Mapped[str | None] = mapped_column(String(20), nullable=True)
    headliner_artist: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_attendance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peak_hour_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    peak_hour_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    opening_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closing_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    event = relationship("Event", back_populates="event_days")
