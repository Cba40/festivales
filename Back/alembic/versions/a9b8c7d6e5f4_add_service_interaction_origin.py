"""add interaction_type and origin to service_interaction_log

Agrega las dimensiones que permiten separar actividad del usuario real
(screen_open / filter_change) de los requests técnicos del sistema
(prefetch / SWR / polling) en la tabla de interacciones.

ADITIVO: solo agrega dos columnas con server_default no destructivo.
Las filas históricas quedan automáticamente con interaction_type='request'
y origin='system'.

Revision ID: a9b8c7d6e5f4
Revises: a7b8c9d0e1f2
Create Date: 2026-09-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'service_interaction_log',
        sa.Column('interaction_type', sa.String(16), nullable=False, server_default=sa.text("'request'")),
    )
    op.add_column(
        'service_interaction_log',
        sa.Column('origin', sa.String(16), nullable=False, server_default=sa.text("'system'")),
    )


def downgrade() -> None:
    op.drop_column('service_interaction_log', 'origin')
    op.drop_column('service_interaction_log', 'interaction_type')