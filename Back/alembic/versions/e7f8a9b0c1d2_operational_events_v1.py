"""operational_events V1: effect model

Revision ID: e7f8a9b0c1d2
Revises: d1e2f3a4b5c6
Create Date: 2026-09-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7f8a9b0c1d2'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0. Eliminar constraints e índice que referencian columnas legacy
    op.drop_constraint('ck_oe_start_min_ge_0', 'operational_events', type_='check')
    op.drop_constraint('ck_oe_end_min_gt_start', 'operational_events', type_='check')
    op.drop_index('ix_oe_event_day_active', table_name='operational_events')

    # 1. Eliminar columnas legacy
    op.drop_column('operational_events', 'start_min')
    op.drop_column('operational_events', 'end_min')

    # 2. Ajustar columnas existentes al modelo V1
    #    description pasa a ser opcional
    op.alter_column(
        'operational_events', 'description',
        existing_type=sa.Text(), nullable=True, server_default=None,
    )
    #    zone_id pasa a ser obligatoria (sin ON DELETE SET NULL)
    op.drop_constraint('fk_oe_zone_id', 'operational_events', type_='foreignkey')
    op.alter_column(
        'operational_events', 'zone_id',
        existing_type=sa.String(36), nullable=False,
    )
    op.create_foreign_key(
        'fk_oe_zone_id', 'operational_events', 'zones',
        ['zone_id'], ['id'],
    )
    #    timestamps con zona horaria
    op.alter_column(
        'operational_events', 'created_at',
        existing_type=sa.DateTime(), type_=sa.DateTime(timezone=True),
    )
    op.alter_column(
        'operational_events', 'updated_at',
        existing_type=sa.DateTime(), type_=sa.DateTime(timezone=True),
    )

    # 3. Agregar nuevas columnas
    op.add_column('operational_events', sa.Column('effect_type', sa.String(30), nullable=False))
    op.add_column('operational_events', sa.Column('effect_value', sa.Integer(), nullable=True))
    op.add_column('operational_events', sa.Column('is_incident', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('operational_events', sa.Column('start_timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column('operational_events', sa.Column('end_timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    #    Los server_default de start/end_timestamp son temporales (tabla vacía);
    #    el modelo los define sin default para la ventana temporal.
    op.alter_column('operational_events', 'start_timestamp', server_default=None)
    op.alter_column('operational_events', 'end_timestamp', server_default=None)

    # 4. Agregar constraints CHECK
    op.create_check_constraint(
        'ck_operational_events_temporal',
        'operational_events',
        sa.text('end_timestamp > start_timestamp'),
    )
    op.create_check_constraint(
        'ck_operational_events_effect_value',
        'operational_events',
        sa.text(
            "(effect_type = 'reduccion_capacidad' AND effect_value IS NOT NULL AND effect_value BETWEEN 1 AND 100) OR "
            "(effect_type = 'cierre_total' AND effect_value IS NULL) OR "
            "(effect_type = 'aumento_demanda' AND effect_value IS NOT NULL AND effect_value >= 1) OR "
            "(effect_type = 'incidente_sin_impacto' AND effect_value IS NULL)"
        ),
    )

    # 5. Agregar índices
    op.create_index('ix_operational_events_event_day_id', 'operational_events', ['event_day_id'])
    op.create_index('ix_operational_events_zone_id', 'operational_events', ['zone_id'])
    op.create_index(
        'ix_operational_events_active_window',
        'operational_events',
        ['is_active', 'start_timestamp', 'end_timestamp'],
        postgresql_where=sa.text('is_active = true'),
    )


def downgrade() -> None:
    # 1. Eliminar índices
    op.drop_index('ix_operational_events_active_window', table_name='operational_events')
    op.drop_index('ix_operational_events_zone_id', table_name='operational_events')
    op.drop_index('ix_operational_events_event_day_id', table_name='operational_events')

    # 2. Eliminar constraints
    op.drop_constraint('ck_operational_events_effect_value', 'operational_events', type_='check')
    op.drop_constraint('ck_operational_events_temporal', 'operational_events', type_='check')

    # 3. Eliminar columnas nuevas
    op.drop_column('operational_events', 'end_timestamp')
    op.drop_column('operational_events', 'start_timestamp')
    op.drop_column('operational_events', 'is_incident')
    op.drop_column('operational_events', 'effect_value')
    op.drop_column('operational_events', 'effect_type')

    # 4. Revertir timestamps a sin zona horaria
    op.alter_column(
        'operational_events', 'updated_at',
        existing_type=sa.DateTime(timezone=True), type_=sa.DateTime(),
    )
    op.alter_column(
        'operational_events', 'created_at',
        existing_type=sa.DateTime(timezone=True), type_=sa.DateTime(),
    )

    # 5. Revertir zone_id a nullable con ON DELETE SET NULL
    op.drop_constraint('fk_oe_zone_id', 'operational_events', type_='foreignkey')
    op.alter_column(
        'operational_events', 'zone_id',
        existing_type=sa.String(36), nullable=True,
    )
    op.create_foreign_key(
        'fk_oe_zone_id', 'operational_events', 'zones',
        ['zone_id'], ['id'], ondelete='SET NULL',
    )

    # 6. Revertir description a obligatoria con default
    op.alter_column(
        'operational_events', 'description',
        existing_type=sa.Text(), nullable=False, server_default='',
    )

    # 7. Restaurar columnas legacy
    op.add_column('operational_events', sa.Column('end_min', sa.Integer(), nullable=True))
    op.add_column('operational_events', sa.Column('start_min', sa.Integer(), nullable=False))

    # 8. Restaurar índice y constraints legacy
    op.create_index(
        'ix_oe_event_day_active',
        'operational_events',
        ['event_day_id', 'is_active'],
        postgresql_where=sa.text('is_active = true'),
    )
    op.create_check_constraint(
        'ck_oe_end_min_gt_start', 'operational_events',
        'end_min IS NULL OR end_min > start_min',
    )
    op.create_check_constraint(
        'ck_oe_start_min_ge_0', 'operational_events',
        'start_min >= 0',
    )
