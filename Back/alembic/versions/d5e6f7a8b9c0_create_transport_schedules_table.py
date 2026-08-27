"""Crear tabla transport_schedules (S1 Transporte V1 - PARTE 3)

Horarios específicos de transporte público. Cada fila representa un
servicio concreto asociado a una parada de línea (transport_line_stops).

El destino vive en esta tabla (no existe tabla separada de destinos).
Los horarios son específicos (no frecuencias calculadas).

ADITIVO: crea una tabla nueva. No modifica tablas ni datos existentes.
Idempotente a nivel esquema vía alembic (create/drop simétricos).

Revision ID: d5e6f7a8b9c0
Revises: c3d4e5f6a7b8
Create Date: 2026-08-26 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'd5e6f7a8b9c0'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'transport_schedules',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('line_stop_id', sa.String(36),
                  sa.ForeignKey('transport_line_stops.id', ondelete='CASCADE'), nullable=False),
        sa.Column('day_type', sa.String(20), nullable=False),
        sa.Column('departure_time', sa.Time(), nullable=False),
        sa.Column('destination', sa.String(100), nullable=False),
        sa.UniqueConstraint('line_stop_id', 'day_type', 'departure_time', 'destination',
                            name='uq_transport_schedules_line_stop_schedule'),
    )
    op.create_index('idx_ts_line_stop', 'transport_schedules', ['line_stop_id'])
    op.create_index('idx_ts_day_type', 'transport_schedules', ['day_type'])


def downgrade() -> None:
    op.drop_index('idx_ts_day_type', table_name='transport_schedules')
    op.drop_index('idx_ts_line_stop', table_name='transport_schedules')
    op.drop_table('transport_schedules')
