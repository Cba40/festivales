"""create operator_messages table (Alerts & Messages V1)

Nueva tabla de mensajes programables del operador dirigidos al público.

ADITIVO: crea una tabla nueva. No modifica tablas ni datos existentes.
Idempotente a nivel esquema vía alembic (create/drop simétricos).

Revision ID: f5f7b8d0e1c2
Revises: e4e6a8c1f2b3
Create Date: 2026-09-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'f5f7b8d0e1c2'
down_revision: Union[str, Sequence[str], None] = 'e4e6a8c1f2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'operator_messages',
        sa.Column('id', sa.UUID(),
                  primary_key=True, server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('event_id', sa.String(36),
                  sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('line_id', sa.String(36),
                  sa.ForeignKey('transport_lines.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default=sa.text("'draft'")),
        sa.Column('priority', sa.String(20), nullable=False, server_default=sa.text("'normal'")),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('publish_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_check_constraint(
        'check_message_temporal',
        'operator_messages',
        sa.text('expires_at IS NULL OR expires_at > publish_at'),
    )
    op.create_check_constraint(
        'check_message_status',
        'operator_messages',
        sa.text("status IN ('draft', 'published', 'cancelled')"),
    )
    op.create_check_constraint(
        'check_message_priority',
        'operator_messages',
        sa.text("priority IN ('normal', 'high', 'urgent')"),
    )
    op.create_index(
        'ix_messages_published_window',
        'operator_messages',
        ['status', 'publish_at', 'expires_at'],
        postgresql_where=sa.text("status = 'published'"),
    )


def downgrade() -> None:
    op.drop_index('ix_messages_published_window', table_name='operator_messages')
    op.drop_constraint('check_message_priority', 'operator_messages', type_='check')
    op.drop_constraint('check_message_status', 'operator_messages', type_='check')
    op.drop_constraint('check_message_temporal', 'operator_messages', type_='check')
    op.drop_table('operator_messages')