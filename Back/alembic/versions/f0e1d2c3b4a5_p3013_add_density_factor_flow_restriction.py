"""p3013: Add density_factor and flow_restriction columns to zone_behaviors

Revision ID: f0e1d2c3b4a5
Revises: e5f6a7b8c9d0
Create Date: 2026-07-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f0e1d2c3b4a5'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('zone_behaviors', sa.Column('density_factor', sa.Float(), nullable=False, server_default=sa.text('0.5')))
    op.add_column('zone_behaviors', sa.Column('flow_restriction', sa.String(20), nullable=False, server_default=sa.text("'OPEN'")))
    op.create_check_constraint('ck_zb_density_factor_range', 'zone_behaviors',
                                'density_factor >= 0.0 AND density_factor <= 1.0')
    op.create_check_constraint('ck_zb_flow_restriction', 'zone_behaviors',
                                "flow_restriction IN ('OPEN', 'REGULATED', 'CLOSED')")


def downgrade() -> None:
    op.drop_constraint('ck_zb_flow_restriction', 'zone_behaviors', type_='check')
    op.drop_constraint('ck_zb_density_factor_range', 'zone_behaviors', type_='check')
    op.drop_column('zone_behaviors', 'flow_restriction')
    op.drop_column('zone_behaviors', 'density_factor')
