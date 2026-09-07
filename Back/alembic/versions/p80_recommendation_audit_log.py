"""p80 — Create recommendation_audit_log table.

Revision ID: p80
Revises: p70
Create Date: 2026-09-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'p80'
down_revision: Union[str, Sequence[str], None] = 'p70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'recommendation_audit_log',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('recommendation_id', sa.UUID(), nullable=False),
        sa.Column('action', sa.VARCHAR(length=30), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('operator_id', sa.VARCHAR(length=100), nullable=True),
        sa.Column('justification', sa.TEXT(), nullable=True),
        sa.Column('metrics_snapshot', sa.JSON(), nullable=True),
        sa.Column('input_data_snapshot', sa.JSON(), nullable=True),
        sa.Column('km_version', sa.UUID(), nullable=True),
        sa.Column('algorithm_version', sa.VARCHAR(length=50), nullable=True),
        sa.Column('llm_version', sa.VARCHAR(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "action IN ('generated', 'notified', 'review_started', 'resolved')",
            name='valid_action'
        ),
        sa.ForeignKeyConstraint(
            ['recommendation_id'],
            ['configuration_recommendations.id'],
        ),
    )
    op.create_index(
        'idx_audit_rec_id',
        'recommendation_audit_log',
        ['recommendation_id'],
    )
    op.create_index(
        'idx_audit_timestamp',
        'recommendation_audit_log',
        ['timestamp'],
    )


def downgrade() -> None:
    op.drop_index('idx_audit_timestamp', table_name='recommendation_audit_log')
    op.drop_index('idx_audit_rec_id', table_name='recommendation_audit_log')
    op.drop_table('recommendation_audit_log')