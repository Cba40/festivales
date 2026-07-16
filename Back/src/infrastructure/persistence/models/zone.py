from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base


class ZoneModel(Base):
    __tablename__ = "zones"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    zone_type_id: Mapped[UUID] = mapped_column(ForeignKey("zone_types.id"), nullable=False)
    capacity: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (
        CheckConstraint("capacity > 0", name="ck_zones_capacity_positive"),
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    zone_type: Mapped["ZoneTypeModel"] = relationship(back_populates="zones")
    operational_events: Mapped[list["OperationalEventModel"]] = relationship(back_populates="target_zone")
