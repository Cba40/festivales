import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.db.session import Base


class IncidentImpact(Base):
    __tablename__ = "incident_impacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id"), nullable=False)
    zone_type_id: Mapped[str] = mapped_column(String(36), ForeignKey("zone_types.id"), nullable=False)
    saturation_delta: Mapped[float] = mapped_column(Float, nullable=False)
    attendance_delta: Mapped[float] = mapped_column(Float, nullable=False)
    resource_delta: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    incident = relationship("Incident", backref=backref("incident_impacts", lazy="selectin"))
    zone_type = relationship("ZoneType", back_populates="incident_impacts")

    __table_args__ = (
        Index("ix_incident_impact_incident_id", "incident_id"),
        Index("ix_incident_impact_zone_type_id", "zone_type_id"),
    )
