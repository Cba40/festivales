"""add_geometry_fields_to_zones

Revision ID: 4d5e6f7a8b9c
Revises: 3c4d5e6f7a8b
Create Date: 2026-06-13 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4d5e6f7a8b9c'
down_revision: Union[str, Sequence[str], None] = '3c4d5e6f7a8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('zones', sa.Column('geometry_type', sa.String(length=10), nullable=True))
    op.add_column('zones', sa.Column('coordinates', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('zones', 'coordinates')
    op.drop_column('zones', 'geometry_type')
