"""pXX — Add density_deviation_threshold to recommendation_config.

Revision ID: d6e5f4c3b2a1
Revises: 2b3c4d5e6f7a
Create Date: 2026-09-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd6e5f4c3b2a1'
down_revision: Union[str, Sequence[str], None] = '2b3c4d5e6f7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'recommendation_config',
        sa.Column(
            'density_deviation_threshold',
            sa.Float(),
            nullable=False,
            server_default='0.2',
        ),
    )


def downgrade() -> None:
    op.drop_column('recommendation_config', 'density_deviation_threshold')