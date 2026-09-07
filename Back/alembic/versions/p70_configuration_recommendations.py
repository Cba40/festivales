"""p70 — Create configuration_recommendations table.

Revision ID: p70
Revises: d6e5f4c3b2a1
Create Date: 2026-09-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'p70'
down_revision: Union[str, Sequence[str], None] = 'd6e5f4c3b2a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'configuration_recommendations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('target_entity_type', sa.VARCHAR(length=50), nullable=False),
        sa.Column('target_entity_id', sa.VARCHAR(length=36)),
        sa.Column('proposed_change', sa.TEXT(), nullable=False),
        sa.Column('recommendation_type', sa.VARCHAR(length=50), nullable=False),
        sa.Column('supporting_metrics', sa.JSON(), nullable=False),
        sa.Column('historic_trace', sa.JSON(), nullable=False),
        sa.Column('recommendation_confidence', sa.FLOAT(), nullable=False),
        sa.Column('status', sa.VARCHAR(length=30), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('km_version_analyzed', sa.UUID(), nullable=True),
        sa.Column('algorithm_version', sa.VARCHAR(length=50), nullable=True),
        sa.Column('event_ids', sa.JSON(), nullable=True),
        sa.Column('resolved_by', sa.VARCHAR(length=100), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution_justification', sa.TEXT(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "status IN ('pending_review', 'approved', 'rejected')",
            name='valid_status'
        ),
        sa.CheckConstraint(
            "recommendation_type IN ('parameter_adjustment', 'new_configuration', 'configuration_removal', 'data_quality_improvement', 'coverage_improvement')",
            name='valid_recommendation_type'
        ),
    )
    op.create_index(
        'idx_config_rec_status',
        'configuration_recommendations',
        ['status'],
    )
    op.create_index(
        'idx_config_rec_type',
        'configuration_recommendations',
        ['recommendation_type'],
    )
    op.create_index(
        'idx_config_rec_generated',
        'configuration_recommendations',
        ['generated_at'],
    )


def downgrade() -> None:
    op.drop_index('idx_config_rec_generated', table_name='configuration_recommendations')
    op.drop_index('idx_config_rec_type', table_name='configuration_recommendations')
    op.drop_index('idx_config_rec_status', table_name='configuration_recommendations')
    op.drop_table('configuration_recommendations')