"""p51: Remove start_min and end_min from operational_phases

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-07-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3c4d5e6f7a8b'
down_revision: Union[str, Sequence[str], None] = '2b3c4d5e6f7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('operational_phases', 'start_min')
    op.drop_column('operational_phases', 'end_min')


def downgrade() -> None:
    op.add_column('operational_phases', sa.Column('start_min', sa.Integer(), nullable=False))
    op.add_column('operational_phases', sa.Column('end_min', sa.Integer(), nullable=False))
