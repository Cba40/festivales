"""p93 — drop dead config columns from recommendation_config and stage4_config.

Elimina los campos que la auditoría confirmó como código muerto (ningún módulo
del backend los lee):

* recommendation_config.density_deviation_threshold
* stage4_config.confidence_no_events
* stage4_config.confidence_planned_events
* stage4_config.confidence_incident
* stage4_config.wait_time_mapping

Revision ID: p93
Revises: p92
Create Date: 2026-09-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'p93'
down_revision: Union[str, Sequence[str], None] = 'p92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('recommendation_config', 'density_deviation_threshold')
    op.drop_column('stage4_config', 'confidence_no_events')
    op.drop_column('stage4_config', 'confidence_planned_events')
    op.drop_column('stage4_config', 'confidence_incident')
    op.drop_column('stage4_config', 'wait_time_mapping')


def downgrade() -> None:
    op.add_column(
        'stage4_config',
        sa.Column('wait_time_mapping', sa.JSON(), nullable=False, server_default='[]'),
    )
    op.add_column(
        'stage4_config',
        sa.Column('confidence_incident', sa.Float(), nullable=False, server_default='0.5'),
    )
    op.add_column(
        'stage4_config',
        sa.Column('confidence_planned_events', sa.Float(), nullable=False, server_default='0.8'),
    )
    op.add_column(
        'stage4_config',
        sa.Column('confidence_no_events', sa.Float(), nullable=False, server_default='1.0'),
    )
    op.add_column(
        'recommendation_config',
        sa.Column(
            'density_deviation_threshold',
            sa.Float(),
            nullable=False,
            server_default='0.2',
        ),
    )