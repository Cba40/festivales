"""p50: Add recommendation_config and stage4_config tables

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-07-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2b3c4d5e6f7a'
down_revision: Union[str, Sequence[str], None] = '1a2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'recommendation_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('low_density_saturation_threshold', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('low_density_reasoning_threshold', sa.Float(), nullable=False, server_default='0.3'),
        sa.Column('regulated_penalty', sa.Float(), nullable=False, server_default='0.3'),
        sa.Column('vip_bonus', sa.Float(), nullable=False, server_default='0.1'),
        sa.Column('staff_bonus', sa.Float(), nullable=False, server_default='0.2'),
        sa.Column('mobility_penalty', sa.Float(), nullable=False, server_default='0.15'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'stage4_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('saturation_high_threshold', sa.Float(), nullable=False, server_default='0.9'),
        sa.Column('saturation_moderate_threshold', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('confidence_no_events', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('confidence_planned_events', sa.Float(), nullable=False, server_default='0.8'),
        sa.Column('confidence_incident', sa.Float(), nullable=False, server_default='0.5'),
        sa.Column('wait_time_mapping', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('stage4_config')
    op.drop_table('recommendation_config')
