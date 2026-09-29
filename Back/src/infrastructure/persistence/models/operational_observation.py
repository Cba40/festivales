from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, func, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class OperationalObservationModel(Base):
    __tablename__ = "operational_observations"

    # Declarados aca y no solo en la migracion: si el indice existe en la base
    # pero no en el modelo, el proximo `alembic revision --autogenerate` lo
    # propone como `op.drop_index` y lo borra. Los nombres coinciden con los de
    # la revision f2a3b4c5d6e7.
    __table_args__ = (
        Index("ix_operational_observations_zone_id_timestamp", "zone_id", "timestamp"),
        Index("ix_operational_observations_timestamp", "timestamp"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    event_day_id: Mapped[str] = mapped_column(String(36), nullable=False)
    zone_id: Mapped[str] = mapped_column(String(36), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observed_density: Mapped[int] = mapped_column(Integer, nullable=False)
    observer_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, server_default="manual")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Auditoría de corrección. Nullable y sin default: NULL significa "nunca se
    # corrigió", que es el caso de la overwhelming mayoría de las filas. Se
    # escribe solo desde el PATCH, no desde el alta.
    corrected_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)