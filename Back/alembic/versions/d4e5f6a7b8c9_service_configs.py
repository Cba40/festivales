"""ServiceConfig — Configuración de servicios para personas.

Tabla de configuración de permanencias de servicios (diseño Baños V1,
SERVICIOS_PERSONAS_DISENO.md §3 / §7):

- Un solo default global por (zone_type_id, subtipo): event_day_id NULL.
- Un solo override por (zone_type_id, subtipo, event_day_id): event_day_id
  referenciando la jornada concreta.
- La unicidad se garantiza con índices parciales (COALESCE sobre subtipo NULL).

Revision ID: d4e5f6a7b8c9
Revises: c7d8e9f0a1b2
Create Date: 2026-08-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'service_configs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column(
            'zone_type_id',
            sa.String(36),
            sa.ForeignKey('zone_types.id'),
            nullable=False,
        ),
        sa.Column('subtipo', sa.String(100), nullable=True),
        sa.Column(
            'event_day_id',
            sa.String(36),
            sa.ForeignKey('event_days.id'),
            nullable=True,
        ),
        sa.Column('average_duration_min', sa.Integer, nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Un solo default por (zone_type_id, subtipo): event_day_id NULL.
    op.create_index(
        'uq_service_config_default',
        'service_configs',
        ['zone_type_id', sa.text("COALESCE(subtipo, '')")],
        unique=True,
        postgresql_where=sa.text('event_day_id IS NULL'),
    )

    # Un solo override por (zone_type_id, subtipo, event_day_id).
    op.create_index(
        'uq_service_config_override',
        'service_configs',
        ['zone_type_id', sa.text("COALESCE(subtipo, '')"), 'event_day_id'],
        unique=True,
        postgresql_where=sa.text('event_day_id IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_service_config_override', table_name='service_configs')
    op.drop_index('uq_service_config_default', table_name='service_configs')
    op.drop_table('service_configs')