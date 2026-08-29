"""Crear tabla emergency_protocols (Emergencia V2 - Fase S1)

Catálogo de protocolos de emergencia por contexto (festival / transporte /
hospedaje). Cada protocolo tiene pasos accionables (JSONB), prioridad 1-3,
orden no negativo y un ``target_type`` opcional que REUTILIZA el enum
``emergency_type`` creado en V1 (no se recrea, por eso ``create_type=False``).

Sujeto a: UNIQUE(context, title), CHECK(priority IN (1,2,3)), CHECK(order >= 0).
En ``order`` (palabra reservada) se requiere el identificador entre comillas.

ADITIVO: crea una tabla nueva y un enum propio. No modifica tablas ni datos
existentes. El downgrade es simétrico pero NO dropea ``emergency_type`` (V1).

Revision ID: c8d9e0f1a2b3
Revises: b6c7d8e9f0a1
Create Date: 2026-08-29 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB


revision: str = 'c8d9e0f1a2b3'
down_revision: Union[str, Sequence[str], None] = 'b6c7d8e9f0a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'emergency_protocols',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('context',
                  sa.Enum('festival', 'transporte', 'hospedaje',
                          name='emergency_protocol_context'),
                  nullable=False),
        sa.Column('title', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('icon', sa.String(10), nullable=False),
        sa.Column('steps', JSONB(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('target_type',
                  postgresql.ENUM(
                      'policia', 'bomberos', 'salud', 'defensa_civil',
                      'numero_emergencia', 'otro',
                      name='emergency_type',
                      create_type=False
                  ),
                  nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('context', 'title', name='uq_emergency_protocols_context_title'),
        sa.CheckConstraint('priority IN (1, 2, 3)', name='ck_emergency_protocols_priority'),
        sa.CheckConstraint('"order" >= 0', name='ck_emergency_protocols_order'),
    )


def downgrade() -> None:
    op.drop_table('emergency_protocols')
    op.execute('DROP TYPE IF EXISTS emergency_protocol_context')