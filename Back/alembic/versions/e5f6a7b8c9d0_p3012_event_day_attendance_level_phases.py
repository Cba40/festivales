"""p3012: Add attendance_level_id to event_days + create event_day_phases table

Revision ID: e5f6a7b8c9d0
Revises: 2c4cf795dc37
Create Date: 2026-07-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = '2c4cf795dc37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Add attendance_level_id to event_days ──────────────────────
    op.add_column(
        "event_days",
        sa.Column("attendance_level_id", sa.String(36), sa.ForeignKey("attendance_levels.id"), nullable=False),
    )

    # ── Create event_day_phases table ───────────────────────────────
    op.create_table(
        "event_day_phases",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("event_day_id", sa.String(36), sa.ForeignKey("event_days.id", ondelete="CASCADE"), nullable=False),
        sa.Column("operational_phase_id", UUID(as_uuid=True), sa.ForeignKey("operational_phases.id"), nullable=False),
        sa.Column("start_min", sa.Integer(), nullable=False),
        sa.Column("end_min", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("start_min >= 0", name="ck_edp_start_min_non_negative"),
        sa.CheckConstraint("end_min > start_min", name="ck_edp_end_min_gt_start_min"),
    )


def downgrade() -> None:
    op.drop_table("event_day_phases")
    op.drop_column("event_days", "attendance_level_id")
