"""Crear tabla transport_lines (S1 Transporte V1 - PARTE 1)

Catálogo de líneas de transporte público por evento. Cada línea pertenece a
un evento, tiene un nombre único dentro de éste, un tipo (urbano /
interurbano), la empresa operadora y opcionalmente un color hex.

ADITIVO: crea una tabla nueva. No modifica tablas ni datos existentes.
Idempotente a nivel esquema vía alembic (create/drop simétricos).

La tabla transport_line_stops (PARTE 2) y transport_schedules (PARTE 3)
se crean en migraciones subsiguientes con down_revision encadenada.

Revision ID: a1b2c3d4e5f6
Revises: c9d3e7f1a5b8
Create Date: 2026-08-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'c9d3e7f1a5b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transport_lines',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('event_id', sa.String(36),
                  sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('type', sa.String(20), nullable=False),
        sa.Column('company', sa.String(100), nullable=False),
        sa.Column('color', sa.String(7), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('event_id', 'name', name='uq_transport_lines_event_name'),
    )
    op.create_index(
        'idx_transport_lines_event',
        'transport_lines',
        ['event_id'],
    )


def downgrade() -> None:
    op.drop_index('idx_transport_lines_event', table_name='transport_lines')
    op.drop_table('transport_lines')
