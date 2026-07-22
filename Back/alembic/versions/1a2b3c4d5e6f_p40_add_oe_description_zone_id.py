"""p40: Add description and zone_id columns to operational_events

Revision ID: 1a2b3c4d5e6f
Revises: f0e1d2c3b4a5
Create Date: 2026-07-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, Sequence[str], None] = 'f0e1d2c3b4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('operational_events', sa.Column('description', sa.Text(), nullable=False, server_default=''))
    op.add_column('operational_events', sa.Column('zone_id', sa.String(36), nullable=True))
    op.create_foreign_key(
        'fk_oe_zone_id', 'operational_events', 'zones',
        ['zone_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_oe_zone_id', 'operational_events', type_='foreignkey')
    op.drop_column('operational_events', 'zone_id')
    op.drop_column('operational_events', 'description')
