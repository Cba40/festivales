"""EventDay: Representa una jornada operativa territorial."""
import uuid
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EventDay(Base):
    """Representa una jornada operativa territorial.

    Aggregate Root administrativo del Contexto Operacional.
    Posee EventDayPhase (composicion interna), referencia OperationalProfile,
    AttendanceLevel y Event. Pertenece a cero o muchos OperationalEvent.
    """
    __tablename__ = "event_days"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    day_of_week: Mapped[str] = mapped_column(String(10), nullable=False)
    weather: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    headliner_artist: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    estimated_attendance: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    operational_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("operational_profiles.id"), nullable=False,
    )
    attendance_level_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("attendance_levels.id"), nullable=False,
    )
    operational_start_min: Mapped[int] = mapped_column(Integer, nullable=False)
    operational_end_min: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    event = relationship("Event", back_populates="event_days")
    operational_profile: Mapped["OperationalProfile"] = relationship()
    attendance_level: Mapped["AttendanceLevel"] = relationship()
    phases: Mapped[list["EventDayPhase"]] = relationship(
        back_populates="event_day", cascade="all, delete-orphan",
    )
    operational_events: Mapped[list["OperationalEvent"]] = relationship(
        back_populates="event_day", cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("event_id", "date", name="uq_event_day_event_date"),
        Index("ix_event_day_event_active", "event_id", "is_active", postgresql_where=text("is_active = true")),
    )
