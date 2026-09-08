from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Integer, JSON, func, String, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import UniqueConstraint

from src.infrastructure.db.base import Base


class KnowledgeModelVersionModel(Base):
    __tablename__ = "knowledge_model_versions"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("nextval('km_version_number_seq')"),
    )
    snapshot_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(100), nullable=True)

    __table_args__ = (
        UniqueConstraint("snapshot_hash", name="uq_km_versions_snapshot_hash"),
    )