import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AttendanceLevel(Base):
    __tablename__ = "attendance_levels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_day_id: Mapped[str] = mapped_column(String(36), ForeignKey("event_days.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    min_people: Mapped[int] = mapped_column(Integer, nullable=False)
    max_people: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    event_day = relationship("EventDay", back_populates="attendance_levels")

    __table_args__ = (
        UniqueConstraint("event_day_id", "name", name="uq_attendance_level_event_day_name"),
        UniqueConstraint("event_day_id", "min_people", "max_people", name="uq_attendance_level_range"),
    )