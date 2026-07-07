"""P4 — Índices faltantes en tabla incidents

Crea índices compuestos para queries frecuentes sobre incidentes
que no fueron incluidos en la migración P2 original.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Índice compuesto para filtrar incidentes activos por evento
    # (usado en context_engine._apply_incident_corrections)
    op.create_index(
        'ix_incident_event_status',
        'incidents',
        ['event_id', 'status'],
        postgresql_where=sa.text("status IN ('abierto', 'en_curso')"),
    )

    # Índice para lookup de incidentes por zona
    op.create_index(
        'ix_incident_zone_id',
        'incidents',
        ['zone_id'],
    )


def downgrade() -> None:
    op.drop_index('ix_incident_event_status', table_name='incidents')
    op.drop_index('ix_incident_zone_id', table_name='incidents')
