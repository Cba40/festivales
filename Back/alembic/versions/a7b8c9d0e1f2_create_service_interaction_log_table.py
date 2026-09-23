"""create service_interaction_log table (Analytics - Interacción de servicios)

Tabla APPEND-ONLY de interacciones digitales anónimas con servicios
municipales. Una fila por request efectivo a un endpoint público de producto
(parking, gastronomía, baños, hidratación, descanso, transporte, salida,
alojamiento, emergencia).

ADITIVO: crea una tabla nueva. No modifica tablas ni datos existentes.
Idempotente a nivel esquema vía alembic (create/drop simétricos).

Revision ID: a7b8c9d0e1f2
Revises: f5f7b8d0e1c2
Create Date: 2026-09-23

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f5f7b8d0e1c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'service_interaction_log',
        sa.Column('id', sa.UUID(),
                  primary_key=True, server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('event_id', sa.String(36), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('service_category', sa.String(50), nullable=False),
        sa.Column('result_status', sa.String(12), nullable=False),
        sa.Column('result_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('request_mode', sa.String(50), nullable=True),
        sa.Column('zone_ids', postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.create_index(
        'ix_service_interaction_event_category_time',
        'service_interaction_log',
        ['event_id', 'service_category', 'timestamp'],
    )
    op.create_index(
        'ix_service_interaction_timestamp',
        'service_interaction_log',
        ['timestamp'],
    )
    op.create_index(
        'ix_service_interaction_result_status',
        'service_interaction_log',
        ['result_status'],
    )


def downgrade() -> None:
    op.drop_index('ix_service_interaction_result_status', table_name='service_interaction_log')
    op.drop_index('ix_service_interaction_timestamp', table_name='service_interaction_log')
    op.drop_index('ix_service_interaction_event_category_time', table_name='service_interaction_log')
    op.drop_table('service_interaction_log')