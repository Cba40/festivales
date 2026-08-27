"""Crear tabla transport_line_stops (S1 Transporte V1 - PARTE 2)

Relación N:N entre líneas de transporte (transport_lines) y paradas
(zones con type='transporte'). Cada registro indica que una parada
pertenece a una línea con un stop_order que define el orden en el
recorrido.

La parada es una Zone existente; NO se crea entidad TransportStop.

ADITIVO: crea una tabla nueva. No modifica tablas ni datos existentes.
Idempotente a nivel esquema vía alembic (create/drop simétricos).

La tabla transport_schedules (PARTE 3) se crea en migración subsiguiente
con down_revision encadenada.

Revision ID: c3d4e5f6a7b8
Revises: f1a2b3c4d5e6
Create Date: 2026-08-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transport_line_stops',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('line_id', sa.String(36),
                  sa.ForeignKey('transport_lines.id', ondelete='CASCADE'), nullable=False),
        sa.Column('zone_id', sa.String(36),
                  sa.ForeignKey('zones.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stop_order', sa.Integer(), nullable=False),
        sa.UniqueConstraint('line_id', 'zone_id', name='uq_transport_line_stops_line_zone'),
        sa.UniqueConstraint('line_id', 'stop_order', name='uq_transport_line_stops_line_order'),
    )
    op.create_index('idx_tls_line', 'transport_line_stops', ['line_id'])
    op.create_index('idx_tls_zone', 'transport_line_stops', ['zone_id'])


def downgrade() -> None:
    op.drop_index('idx_tls_zone', table_name='transport_line_stops')
    op.drop_index('idx_tls_line', table_name='transport_line_stops')
    op.drop_table('transport_line_stops')
