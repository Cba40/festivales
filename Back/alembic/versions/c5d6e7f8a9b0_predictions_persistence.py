"""predictions: tabla persistente de TerritorialPrediction agrupada por EventDay

Fase 0 / Punto 3 y 4 — RFC-004 §4.2, RFC-006 §6.2:
Crea la tabla `predictions` en la cadena raíz (legacy) para volver persistente
el value object TerritorialPrediction generado por el Context Engine,
anclándolo a la jornada operativa (event_day_id) que lo produjo.

Revision ID: c5d6e7f8a9b0
Revises: f7a8b9c0d1e2
Create Date: 2026-09-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = 'c5d6e7f8a9b0'
down_revision: Union[str, Sequence[str], None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "predictions",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), unique=True, nullable=False),
        sa.Column("event_day_id", sa.String(36), sa.ForeignKey("event_days.id"), nullable=False),
        sa.Column("active_phase_id", UUID(as_uuid=True), nullable=False),
        sa.Column("active_event_day_phase_id", UUID(as_uuid=True), nullable=False),
        sa.Column("zone_states_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_unique_constraint(
        "uq_predictions_timestamp", "predictions", ["timestamp"]
    )
    op.create_index(
        "ix_predictions_event_day_id", "predictions", ["event_day_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_predictions_event_day_id", table_name="predictions")
    op.drop_constraint(
        "uq_predictions_timestamp", "predictions", type_="unique"
    )
    op.drop_table("predictions")