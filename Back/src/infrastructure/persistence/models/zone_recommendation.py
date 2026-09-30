from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.base import Base


class ZoneRecommendationModel(Base):
    __tablename__ = "zone_recommendations"

    id: Mapped[UUID] = mapped_column(primary_key=True, server_default=func.gen_random_uuid())
    # `event_day_id` y `zone_id` NO declaran ForeignKey a proposito, aunque p92 las
    # crea en la base. Este modelo vive en `SrcBase` y las tablas que referencia
    # (`event_days`, `zones`) viven en `AppBase`: SQLAlchemy resuelve el string de
    # una FK dentro del MetaData donde se define la tabla, y al no estar en el
    # mismo registro no lo encuentra. El sintoma no es un error al escribir sino
    # un NoReferencedTableError en cuanto se compila el DDL de la tabla (por
    # ejemplo en `alembic autogenerate` o en un test que arme el schema).
    #
    # Antes esto no pasaba porque la capa src/ tenia ademas 9 modelos fantasma
    # P3.0, entre ellos ZoneModel y EventDayModel, que registraban `zones` y
    # `event_days` en `SrcBase.metadata` por accidente. Al borrarlos quedo
    # expuesto. La integridad referencial no se pierde: la siguen aplicando las
    # ForeignKeyConstraint de p92 (líneas 47-53) en Postgres.
    #
    # Este es el mismo criterio que ya usa `OperationalObservationModel` para sus
    # `zone_id` y `event_day_id`. No volver a agregar la FK aqui.
    event_day_id: Mapped[str] = mapped_column(String(36), nullable=False)
    # Neon (y p92, que creo la tabla) lo tienen como timestamptz.
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    zone_id: Mapped[str] = mapped_column(String(36), nullable=False)
    recommendation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[float] = mapped_column(nullable=False)
    ranking: Mapped[int] = mapped_column(nullable=False)
    reasoning: Mapped[list] = mapped_column(JSONB, nullable=False)
    is_nearest: Mapped[bool] = mapped_column(nullable=False, default=False)
    metadata_json: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    # La migracion p92 crea esta columna como timestamptz; el modelo declaraba
    # DateTime naive y quedaba desalineado.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "score >= 0.0 AND score <= 1.0",
            name="ck_zone_recommendations_score_range",
        ),
    )