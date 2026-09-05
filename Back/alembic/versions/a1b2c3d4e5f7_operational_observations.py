"""operational_observations: Create table for operational density observations

Revision ID: a1b2c3d4e5f7
Revises: kmv_000000000001
Create Date: 2026-09-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, Sequence[str], None] = 'kmv_000000000001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operational_observations",
        sa.Column("id", UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("event_day_id", sa.String(36), sa.ForeignKey("event_days.id"), nullable=False),
        sa.Column("zone_id", sa.String(36), sa.ForeignKey("zones.id"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observed_density", sa.Integer(), nullable=False),
        sa.Column("observer_id", sa.String(36), nullable=True),
        sa.Column("source", sa.String(50), nullable=False, server_default="manual"),
        sa.Column("metadata", JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # CHECK constraint
    op.create_check_constraint(
        "ck_operational_observations_density_non_negative",
        "operational_observations",
        sa.text("observed_density >= 0"),
    )

    # Indexes
    op.create_index(
        "ix_operational_observations_event_day_id",
        "operational_observations",
        ["event_day_id"],
    )
    op.create_index(
        "ix_operational_observations_zone_id",
        "operational_observations",
        ["zone_id"],
    )
    op.create_index(
        "ix_operational_observations_timestamp",
        "operational_observations",
        ["timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_operational_observations_timestamp", table_name="operational_observations")
    op.drop_index("ix_operational_observations_zone_id", table_name="operational_observations")
    op.drop_index("ix_operational_observations_event_day_id", table_name="operational_observations")
    op.drop_constraint("ck_operational_observations_density_non_negative", "operational_observations", type_="check")
    op.drop_table("operational_observations")