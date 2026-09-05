from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, func, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.infrastructure.db.base import Base


class ZoneTypeModel(Base):
    __tablename__ = "zone_types"

    # Root chain schema: String(36) IDs
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    icon: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    default_factors: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    # zone_behaviors table DOES exist in root chain (created in d0e1f2a3b4c5)
    zone_behaviors: Mapped[list["ZoneBehaviorModel"]] = relationship(back_populates="zone_type")
    # zones relationship removed - ZoneModel doesn't have zone_type_id FK in root chain
