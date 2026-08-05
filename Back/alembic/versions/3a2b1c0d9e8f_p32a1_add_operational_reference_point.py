"""p32a1: add operational reference point to events

Revision ID: 3a2b1c0d9e8f
Revises: 3007545e07f8
Create Date: 2026-08-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3a2b1c0d9e8f'
down_revision: Union[str, Sequence[str], None] = '3007545e07f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('events', sa.Column('reference_point_latitude', sa.Float(), nullable=True))
    op.add_column('events', sa.Column('reference_point_longitude', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('events', 'reference_point_longitude')
    op.drop_column('events', 'reference_point_latitude')