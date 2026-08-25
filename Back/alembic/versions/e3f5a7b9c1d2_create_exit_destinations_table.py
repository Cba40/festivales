"""Crear tabla exit_destinations (Salir V1 - S1/PARTE 1)

Catálogo de destinos territoriales de egreso por evento. Cada destino es un
lugar real hacia el cual conduce una zona de salida ('Córdoba', 'Colonia
Caroya', etc.). La asociación destino <-> zona de salida se materializa en
S1/PARTE 2 vía tabla intermedia exit_zone_destinations (N:N).

ADITIVO: crea una tabla nueva. No modifica tablas ni datos existentes
(no toca zones: coordenadas/nombres de salidas permanecen intactos).
Idempotente a nivel esquema vía alembic (create/drop simétricos).

Nota de tipos: id y event_id son String(36) siguiendo la convención vigente
(zone_types, zone_subtypes, event_days); events.id es VARCHAR(36), por lo que
el FK debe ser del mismo tipo.

Revision ID: e3f5a7b9c1d2
Revises: b0c1d2e3f4a5
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'e3f5a7b9c1d2'
down_revision: Union[str, Sequence[str], None] = 'b0c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'exit_destinations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('event_id', sa.String(36),
                  sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('event_id', 'name', name='uq_exit_destinations_event_name'),
    )
    op.create_index(
        'idx_exit_destinations_event',
        'exit_destinations',
        ['event_id'],
    )


def downgrade() -> None:
    op.drop_index('idx_exit_destinations_event', table_name='exit_destinations')
    op.drop_table('exit_destinations')
