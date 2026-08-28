"""Crear tablas cities y emergencies (Emergencia V1 - S1)

Catálogo territorial de ciudades y puntos de emergencia. Cada emergencia
pertenece a una ciudad, tiene un nombre único dentro de ésta y un tipo canónico
(EmergencyType: policia / bomberos / salud / defensa_civil / numero_emergencia /
otro). ``latitude`` y ``longitude`` son nullable para soportar números de
emergencia sin ubicación física (911, 107, 100).

ADITIVO: crea tablas nuevas. No modifica tablas ni datos existentes.
Idempotente a nivel esquema vía alembic (create/drop simétricos).

Revision ID: b6c7d8e9f0a1
Revises: aabbccddeeff
Create Date: 2026-08-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'b6c7d8e9f0a1'
down_revision: Union[str, Sequence[str], None] = 'aabbccddeeff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'cities',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('province', sa.String(100), nullable=True),
        sa.Column('country', sa.String(100), nullable=False, server_default='Argentina'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('name', 'province', 'country', name='uq_cities_name_province_country'),
    )

    op.create_table(
        'emergencies',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('city_id', sa.String(36),
                  sa.ForeignKey('cities.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type',
                  sa.Enum('policia', 'bomberos', 'salud', 'defensa_civil',
                          'numero_emergencia', 'otro', name='emergency_type'),
                  nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('emergency_number', sa.String(20), nullable=True),
        sa.Column('address', sa.String(255), nullable=True),
        sa.Column('reference', sa.String(255), nullable=True),
        sa.Column('latitude', sa.Float(), nullable=True),
        sa.Column('longitude', sa.Float(), nullable=True),
        sa.Column('services', sa.String(500), nullable=True),
        sa.Column('schedule', sa.String(100), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('city_id', 'name', name='uq_emergencies_city_name'),
    )
    op.create_index('idx_emergencies_city', 'emergencies', ['city_id'])


def downgrade() -> None:
    op.drop_index('idx_emergencies_city', table_name='emergencies')
    op.drop_table('emergencies')
    op.drop_table('cities')
    op.execute("DROP TYPE IF EXISTS emergency_type")
