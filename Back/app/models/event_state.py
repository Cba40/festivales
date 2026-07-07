import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.db.session import Base


class EventState(Base):
    __tablename__ = "event_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("events.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_initial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_final: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    event = relationship("Event", backref=backref("event_states", lazy="selectin"))
    event_day_zone_factors = relationship("EventDayZoneFactor", back_populates="event_state")
    state_overrides = relationship("StateOverride", back_populates="event_state")

    __table_args__ = (
        UniqueConstraint("event_id", "slug", name="uq_event_state_event_slug"),
        Index("ix_event_state_event_slug", "event_id", "slug"),
    )
