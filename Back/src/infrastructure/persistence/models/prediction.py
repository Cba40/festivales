from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class PredictionModel(Base):
    __tablename__ = "predictions"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    timestamp: Mapped[datetime] = mapped_column(nullable=False, unique=True)
    # Sin ForeignKey: `event_days` vive en `AppBase` y este modelo en `SrcBase`, y
    # SQLAlchemy resuelve las FK dentro del MetaData donde se define la tabla. Con
    # la FK declarada, compilar el DDL de `predictions` levanta
    # NoReferencedTableError. Mismo criterio que `OperationalObservationModel` y
    # `ZoneRecommendationModel`. No volver a agregarla.
    event_day_id: Mapped[str] = mapped_column(String(36), nullable=False)
    knowledge_model_version_id: Mapped[UUID | None] = mapped_column(nullable=True)
    active_phase_id: Mapped[UUID] = mapped_column(nullable=False)
    active_event_day_phase_id: Mapped[UUID] = mapped_column(nullable=False)
    zone_states_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        UniqueConstraint("timestamp", name="uq_predictions_timestamp"),
    )
