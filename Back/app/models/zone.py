# backend/app/models/zone.py

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry

from app.db.session import Base


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    saturation: Mapped[str] = mapped_column(String(20), nullable=False, default="bajo")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="activa")
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    geometry: Mapped[str | None] = mapped_column(Geometry("POLYGON"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    event = relationship("Event", back_populates="zones")
