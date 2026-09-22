"""create transport_alerts table (Alerts & Messages V1)

Nueva tabla de alertas operativas dirigidas al público.

ADITIVO: crea una tabla nueva. No modifica tablas ni datos existentes.
Idempotente a nivel esquema vía alembic (create/drop simétricos).

Revision ID: e4e6a8c1f2b3
Revises: p94
Create Date: 2026-09-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'e4e6a8c1f2b3'
down_revision: Union[str, Sequence[str], None] = 'p94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transport_alerts',
        sa.Column('id', sa.UUID(),
                  primary_key=True, server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('event_id', sa.String(36),
                  sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('line_id', sa.String(36),
                  sa.ForeignKey('transport_lines.id', ondelete='SET NULL'), nullable=True),
        sa.Column('alert_type', sa.String(20), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_check_constraint(
        'check_alert_temporal',
        'transport_alerts',
        sa.text('valid_until > valid_from'),
    )
    op.create_check_constraint(
        'check_alert_type',
        'transport_alerts',
        sa.text("alert_type IN ('info', 'warning', 'disruption', 'closure')"),
    )
    op.create_index(
        'ix_alerts_active_window',
        'transport_alerts',
        ['is_active', 'valid_from', 'valid_until'],
        postgresql_where=sa.text('is_active = true'),
    )


def downgrade() -> None:
    op.drop_index('ix_alerts_active_window', table_name='transport_alerts')
    op.drop_constraint('check_alert_type', 'transport_alerts', type_='check')
    op.drop_constraint('check_alert_temporal', 'transport_alerts', type_='check')
    op.drop_table('transport_alerts')