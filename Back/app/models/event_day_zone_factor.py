import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EventDayZoneFactor(Base):
    __tablename__ = "event_day_zone_factors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_day_id: Mapped[str] = mapped_column(String(36), ForeignKey("event_days.id"), nullable=False)
    zone_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("zone_types.id"), nullable=False)
    event_state_id: Mapped[str] = mapped_column(String(36), ForeignKey("event_states.id"), nullable=False)
    saturation_factor: Mapped[float] = mapped_column(Float, nullable=False)
    attendance_factor: Mapped[float] = mapped_column(Float, nullable=False)
    resource_factor: Mapped[float] = mapped_column(Float, nullable=False)
    priority_weight: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    event_day = relationship("EventDay", back_populates="event_day_zone_factors")
    zone_type = relationship("ZoneType", back_populates="event_day_zone_factors")
    event_state = relationship("EventState", back_populates="event_day_zone_factors")

    __table_args__ = (
        UniqueConstraint("event_day_id", "zone_type_id", "event_state_id", name="uq_edzf_combo"),
        Index("ix_edzf_event_state_id", "event_state_id"),
        Index("ix_edzf_zone_type_id", "zone_type_id"),
    )
