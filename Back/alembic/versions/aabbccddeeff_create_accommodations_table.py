"""Crear tabla accommodations (Hospedaje V1 - S1)

Catálogo de alojamientos de hospedaje por evento. Cada alojamiento pertenece a
un evento, tiene un nombre único dentro de éste y un tipo canónico
(AccommodationType: hotel / hostel / camping / other).

ADITIVO: crea una tabla nueva. No modifica tablas ni datos existentes.
Idempotente a nivel esquema vía alembic (create/drop simétricos).

Revision ID: aabbccddeeff
Revises: d5e6f7a8b9c0
Create Date: 2026-08-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'aabbccddeeff'
down_revision: Union[str, Sequence[str], None] = 'd5e6f7a8b9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'accommodations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('event_id', sa.String(36),
                  sa.ForeignKey('events.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type',
                  sa.Enum('hotel', 'hostel', 'camping', 'other',
                          name='accommodation_type'),
                  nullable=False),
        sa.Column('address', sa.String(255), nullable=True),
        sa.Column('reference', sa.String(255), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('website', sa.String(255), nullable=True),
        sa.Column('official_info_url', sa.String(255), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('event_id', 'name', name='uq_accommodations_event_name'),
    )
    op.create_index('idx_accommodations_event', 'accommodations', ['event_id'])


def downgrade() -> None:
    op.drop_index('idx_accommodations_event', table_name='accommodations')
    op.drop_table('accommodations')
    op.execute("DROP TYPE IF EXISTS accommodation_type")
