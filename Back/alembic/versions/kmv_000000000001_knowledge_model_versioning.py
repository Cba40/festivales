"""knowledge_model_versioning: Create knowledge_model_versions table and FK to predictions

Revision ID: kmv_000000000001
Revises: c5d6e7f8a9b0
Create Date: 2026-09-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = 'kmv_000000000001'
down_revision: Union[str, Sequence[str], None] = 'c5d6e7f8a9b0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. Crear tabla knowledge_model_versions ───────────────────────
    op.create_table(
        "knowledge_model_versions",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("snapshot_data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 2. Agregar FK a predictions ───────────────────────────────────
    op.add_column(
        "predictions",
        sa.Column("knowledge_model_version_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_model_versions.id"), nullable=True),
    )
    op.create_index(
        "ix_predictions_km_version", "predictions", ["knowledge_model_version_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_predictions_km_version", table_name="predictions")
    op.drop_column("predictions", "knowledge_model_version_id")
    op.drop_table("knowledge_model_versions")