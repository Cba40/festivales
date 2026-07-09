import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class StateOverride(Base):
    __tablename__ = "state_overrides"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_day_id: Mapped[str] = mapped_column(String(36), ForeignKey("event_days.id"), nullable=False)
    event_state_id: Mapped[str] = mapped_column(String(36), ForeignKey("event_states.id"), nullable=False)
    zone_type_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("zone_types.id"), nullable=True)
    start_min: Mapped[int] = mapped_column(Integer, nullable=False)
    end_min: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    event_day = relationship("EventDay", back_populates="state_overrides")
    event_state = relationship("EventState", back_populates="state_overrides")
    zone_type = relationship("ZoneType", back_populates="state_overrides")

    __table_args__ = (
        Index("ix_state_override_event_day_minutes", "event_day_id", "start_min", "end_min"),
        Index("ix_state_override_is_active", "is_active", postgresql_where=text("is_active = true")),
    )
