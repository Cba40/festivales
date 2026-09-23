"""create operational_observations table (RFC-006)

Tabla inmutable de observaciones operativas del territorio. Una fila por
observación registrada por el personal operativo (densidad observada por zona
y jornada). No representa automáticamente a todas las personas del territorio:
es una muestra observacional con ``observed_density`` y ``source``.

Py-razón: el modelo ``OperationalObservationModel``
(``src.infrastructure.persistence.models.operational_observation``) ya existía
registrado en el metadata de la cadena P3.0 (``src.infrastructure.db.base.Base``)
pero ninguna migración lo materializaba.

ADITIVO: crea una tabla nueva. No modifica tablas ni datos existentes.
Idempotente a nivel esquema vía alembic (create/drop simétricos).

Revision ID: d9e0f1a2b3c4
Revises: c3d4e5f6a7b8
Create Date: 2026-09-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'd9e0f1a2b3c4'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'operational_observations',
        sa.Column('id', sa.UUID(),
                  primary_key=True, server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('event_day_id', sa.String(36), nullable=False),
        sa.Column('zone_id', sa.String(36), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('observed_density', sa.Integer(), nullable=False),
        sa.Column('observer_id', sa.String(100), nullable=True),
        sa.Column('source', sa.String(50), nullable=False,
                  server_default=sa.text("'manual'")),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('operational_observations')