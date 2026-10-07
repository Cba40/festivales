"""Persist the Bathroom V1 usage-rate hypothesis on service configurations.

Revision ID: a8b9c0d1e2f3
Revises: a7b8c9d0e1f2
Create Date: 2026-10-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INITIAL_BATHROOM_USE_RATE_PER_PERSON_HOUR = 0.1


def upgrade() -> None:
    op.add_column(
        "service_configs",
        sa.Column("bathroom_use_rate_per_person_hour", sa.Float(), nullable=True),
    )
    op.create_check_constraint(
        "ck_service_config_bathroom_use_rate_non_negative",
        "service_configs",
        "bathroom_use_rate_per_person_hour IS NULL OR "
        "bathroom_use_rate_per_person_hour >= 0",
    )
    op.execute(
        sa.text(
            "UPDATE service_configs "
            "SET bathroom_use_rate_per_person_hour = "
            ":initial_rate WHERE subtipo = 'banos'"
        ).bindparams(
            initial_rate=INITIAL_BATHROOM_USE_RATE_PER_PERSON_HOUR
        )
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_service_config_bathroom_use_rate_non_negative",
        "service_configs",
        type_="check",
    )
    op.drop_column("service_configs", "bathroom_use_rate_per_person_hour")
