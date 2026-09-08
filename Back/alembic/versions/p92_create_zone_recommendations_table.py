"""p92 — create zone_recommendations table.

Revision ID: p92
Revises: p91
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'p92'
down_revision: Union[str, Sequence[str], None] = 'p91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'zone_recommendations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('event_day_id', sa.VARCHAR(length=36), nullable=False),
        sa.Column(
            'timestamp',
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column('zone_id', sa.VARCHAR(length=36), nullable=False),
        sa.Column('recommendation_type', sa.VARCHAR(length=50), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('ranking', sa.Integer(), nullable=False),
        sa.Column('reasoning', sa.JSON(), nullable=False),
        sa.Column('is_nearest', sa.Boolean(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text('now()'),
        ),
        sa.CheckConstraint(
            'score >= 0.0 AND score <= 1.0',
            name='ck_zone_recommendations_score_range',
        ),
        sa.ForeignKeyConstraint(
            ['event_day_id'],
            ['event_days.id'],
        ),
        sa.ForeignKeyConstraint(
            ['zone_id'],
            ['zones.id'],
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_zone_recs_event',
        'zone_recommendations',
        ['event_day_id', 'timestamp'],
    )


def downgrade() -> None:
    op.drop_index('idx_zone_recs_event', table_name='zone_recommendations')
    op.drop_table('zone_recommendations')