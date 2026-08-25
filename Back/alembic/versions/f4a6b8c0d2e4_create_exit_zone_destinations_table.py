"""Crear tabla exit_zone_destinations (Salir V1 - S1/PARTE 2)

Tabla de asociación N:N entre zonas de salida (zones.type='salida') y
destinos de egreso (exit_destinations, S1/PARTE 1). Ambos lados borran en
cascada: eliminar una zona o un destino elimina sus relaciones, nunca al
otro extremo.

ADITIVO: crea una tabla nueva sin datos. No modifica tablas ni registros
existentes. Sin columnas extra: solo la PK compuesta (exit_zone_id,
destination_id).

Nota de tipos: ambos IDs son String(36), convención vigente del proyecto
(zones.id y exit_destinations.id son VARCHAR(36)).

Revision ID: f4a6b8c0d2e4
Revises: e3f5a7b9c1d2
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'f4a6b8c0d2e4'
down_revision: Union[str, Sequence[str], None] = 'e3f5a7b9c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'exit_zone_destinations',
        sa.Column('exit_zone_id', sa.String(36),
                  sa.ForeignKey('zones.id', ondelete='CASCADE'), nullable=False),
        sa.Column('destination_id', sa.String(36),
                  sa.ForeignKey('exit_destinations.id', ondelete='CASCADE'), nullable=False),
        sa.PrimaryKeyConstraint('exit_zone_id', 'destination_id'),
    )
    op.create_index('idx_ezd_zone', 'exit_zone_destinations', ['exit_zone_id'])
    op.create_index('idx_ezd_destination', 'exit_zone_destinations', ['destination_id'])


def downgrade() -> None:
    op.drop_index('idx_ezd_destination', table_name='exit_zone_destinations')
    op.drop_index('idx_ezd_zone', table_name='exit_zone_destinations')
    op.drop_table('exit_zone_destinations')
