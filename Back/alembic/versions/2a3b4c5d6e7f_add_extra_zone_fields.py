"""add_extra_zone_fields

Revision ID: 2a3b4c5d6e7f
Revises: 1e040f8557ec
Create Date: 2026-05-30 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, Sequence[str], None] = '1e040f8557ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('zones', sa.Column('disponibilidad', sa.Integer(), nullable=True))
    op.add_column('zones', sa.Column('espera_min', sa.Integer(), nullable=True))
    op.add_column('zones', sa.Column('calle', sa.String(length=255), nullable=True))
    op.add_column('zones', sa.Column('subtipo', sa.String(length=100), nullable=True))
    op.add_column('zones', sa.Column('tipo_culinario', sa.String(length=100), nullable=True))
    op.add_column('zones', sa.Column('x', sa.Float(), nullable=True))
    op.add_column('zones', sa.Column('y', sa.Float(), nullable=True))
    op.add_column('zones', sa.Column('direccion', sa.String(length=255), nullable=True))
    op.add_column('zones', sa.Column('horario', sa.String(length=100), nullable=True))
    op.add_column('zones', sa.Column('telefono', sa.String(length=50), nullable=True))
    op.add_column('zones', sa.Column('servicios', sa.String(length=500), nullable=True))
    op.add_column('zones', sa.Column('transporte', sa.String(length=50), nullable=True))
    op.add_column('zones', sa.Column('capacidad_estimada', sa.Integer(), nullable=True))
    op.add_column('zones', sa.Column('es_embudo', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('zones', 'es_embudo')
    op.drop_column('zones', 'capacidad_estimada')
    op.drop_column('zones', 'transporte')
    op.drop_column('zones', 'servicios')
    op.drop_column('zones', 'telefono')
    op.drop_column('zones', 'horario')
    op.drop_column('zones', 'direccion')
    op.drop_column('zones', 'y')
    op.drop_column('zones', 'x')
    op.drop_column('zones', 'tipo_culinario')
    op.drop_column('zones', 'subtipo')
    op.drop_column('zones', 'calle')
    op.drop_column('zones', 'espera_min')
    op.drop_column('zones', 'disponibilidad')
