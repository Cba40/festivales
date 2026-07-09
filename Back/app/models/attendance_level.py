import uuid
from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AttendanceLevel(Base):
    __tablename__ = "attendance_levels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    min_people: Mapped[int] = mapped_column(Integer, nullable=False)
    max_people: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    global_multiplier: Mapped[float] = mapped_column(Float, nullable=False)

    event = relationship("Event", backref="attendance_levels")

    __table_args__ = (
        UniqueConstraint("event_id", "name", name="uq_attendance_level_event_name"),
        UniqueConstraint("event_id", "min_people", "max_people", name="uq_attendance_level_range"),
    )
