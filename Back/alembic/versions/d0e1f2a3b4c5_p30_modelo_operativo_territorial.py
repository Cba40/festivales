"""P3.0 — Modelo Operativo Territorial.

Reemplazo del modelo temporal basado en espectáculo por
OperationalProfile / OperationalPhase / ZoneBehavior / OperationalEvent.

Revision ID: d0e1f2a3b4c5
Revises: c0d1e2f3a4b5
Create Date: 2026-07-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'c0d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ═══════════════════════════════════════════════
    # 1. TABLAS NUEVAS
    # ═══════════════════════════════════════════════

    # 1.1 operational_profiles (§5.1)
    op.create_table(
        'operational_profiles',
        sa.Column('id', sa.UUID(), primary_key=True,
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # 1.2 operational_phases (§5.2)
    op.create_table(
        'operational_phases',
        sa.Column('id', sa.UUID(), primary_key=True,
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('operational_profile_id', sa.UUID(),
                  sa.ForeignKey('operational_profiles.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('start_min', sa.Integer(), nullable=False),
        sa.Column('end_min', sa.Integer(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),

        sa.UniqueConstraint('operational_profile_id', 'sort_order',
                            name='uq_phase_profile_sort_order'),
    )
    op.create_check_constraint('ck_phase_start_min_ge_0', 'operational_phases',
                               'start_min >= 0')
    op.create_check_constraint('ck_phase_end_min_gt_start', 'operational_phases',
                               'end_min > start_min')
    op.create_check_constraint('ck_phase_sort_order_ge_0', 'operational_phases',
                               'sort_order >= 0')

    # 1.3 zone_behaviors (§5.3)
    op.create_table(
        'zone_behaviors',
        sa.Column('id', sa.UUID(), primary_key=True,
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('operational_phase_id', sa.UUID(),
                  sa.ForeignKey('operational_phases.id', ondelete='CASCADE'),
                  nullable=False),
        # zone_types.id es VARCHAR(36); se usa String(36) por compatibilidad de FK
        sa.Column('zone_type_id', sa.String(36),
                  sa.ForeignKey('zone_types.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('saturation_factor', sa.Numeric(6, 2), nullable=False,
                  server_default=sa.text('1.0')),
        sa.Column('availability_factor', sa.Numeric(6, 2), nullable=False,
                  server_default=sa.text('1.0')),
        sa.Column('resource_factor', sa.Numeric(6, 2), nullable=False,
                  server_default=sa.text('1.0')),
        sa.Column('priority_weight', sa.Numeric(6, 2), nullable=False,
                  server_default=sa.text('1.0')),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),

        sa.UniqueConstraint('operational_phase_id', 'zone_type_id',
                            name='uq_zb_phase_zone_type'),
    )
    op.create_check_constraint('ck_zb_saturation_gt_0', 'zone_behaviors',
                               'saturation_factor > 0')
    op.create_check_constraint('ck_zb_availability_gt_0', 'zone_behaviors',
                               'availability_factor > 0')
    op.create_check_constraint('ck_zb_resource_gt_0', 'zone_behaviors',
                               'resource_factor > 0')
    op.create_check_constraint('ck_zb_priority_gt_0', 'zone_behaviors',
                               'priority_weight > 0')

    # 1.4 operational_events (§5.4)
    op.create_table(
        'operational_events',
        sa.Column('id', sa.UUID(), primary_key=True,
                  server_default=sa.text('gen_random_uuid()'), nullable=False),
        # event_days.id es VARCHAR(36); se usa String(36) por compatibilidad de FK
        sa.Column('event_day_id', sa.String(36),
                  sa.ForeignKey('event_days.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('start_min', sa.Integer(), nullable=False),
        sa.Column('end_min', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False,
                  server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_check_constraint('ck_oe_start_min_ge_0', 'operational_events',
                               'start_min >= 0')
    op.create_check_constraint('ck_oe_end_min_gt_start', 'operational_events',
                               'end_min IS NULL OR end_min > start_min')
    op.create_index(
        'ix_oe_event_day_active',
        'operational_events',
        ['event_day_id', 'is_active'],
        postgresql_where=sa.text('is_active = true'),
    )

    # 1.5 operational_event_modifiers (§5.5)
    op.create_table(
        'operational_event_modifiers',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('zone_type_id', sa.String(36),
                  sa.ForeignKey('zone_types.id', ondelete='SET NULL'),
                  nullable=True),
        sa.Column('saturation_multiplier', sa.Numeric(6, 2), nullable=False,
                  server_default=sa.text('1.0')),
        sa.Column('availability_multiplier', sa.Numeric(6, 2), nullable=False,
                  server_default=sa.text('1.0')),
        sa.Column('priority_modifier', sa.Numeric(6, 2), nullable=False,
                  server_default=sa.text('0.0')),

        sa.UniqueConstraint('event_type', 'zone_type_id',
                            name='uq_oem_event_type_zone_type'),
    )

    # ═══════════════════════════════════════════════
    # 2. MODIFICAR event_days (§5.6)
    # ═══════════════════════════════════════════════

    # 2.1 Agregar nuevas columnas (NOT NULL conforme a §5.6)
    op.add_column('event_days', sa.Column('operational_profile_id', sa.UUID(),
                  sa.ForeignKey('operational_profiles.id'), nullable=False))
    op.add_column('event_days', sa.Column('operational_start_min', sa.Integer(),
                  nullable=False))
    op.add_column('event_days', sa.Column('operational_end_min', sa.Integer(),
                  nullable=False))

    # 2.2 Eliminar CHECK constraint que referencia columnas a remover
    op.drop_constraint('ck_event_day_minute_order', 'event_days', type_='check')

    # 2.3 Eliminar columnas obsoletas
    op.drop_column('event_days', 'entry_start_min')
    op.drop_column('event_days', 'activity_peak_start_min')
    op.drop_column('event_days', 'activity_peak_end_min')
    op.drop_column('event_days', 'exit_start_min')
    op.drop_column('event_days', 'event_end_min')

    # ═══════════════════════════════════════════════
    # 3. ELIMINAR TABLAS OBSOLETAS (§5.7)
    # ═══════════════════════════════════════════════

    # Orden inverso de dependencias
    op.drop_table('event_day_zone_factors')
    op.drop_table('state_overrides')
    op.drop_table('event_states')


def downgrade() -> None:
    # ═══════════════════════════════════════════════
    # 1. RECREAR TABLAS OBSOLETAS
    # ═══════════════════════════════════════════════

    # 1.1 event_states (restaurar desde P2)
    op.create_table(
        'event_states',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('event_id', sa.String(36),
                  sa.ForeignKey('events.id'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('color', sa.String(7), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('is_initial', sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column('is_final', sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column('rules', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),

        sa.UniqueConstraint('event_id', 'slug',
                            name='uq_event_states_event_slug'),
    )

    # 1.2 state_overrides (con columnas INT de P2.0.1)
    op.create_table(
        'state_overrides',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('event_day_id', sa.String(36),
                  sa.ForeignKey('event_days.id'), nullable=False),
        sa.Column('event_state_id', sa.String(36),
                  sa.ForeignKey('event_states.id'), nullable=False),
        sa.Column('zone_type_id', sa.String(36),
                  sa.ForeignKey('zone_types.id'), nullable=True),
        sa.Column('start_min', sa.Integer(), nullable=False),
        sa.Column('end_min', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False,
                  server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_state_override_event_day_minutes', 'state_overrides',
                    ['event_day_id', 'start_min', 'end_min'])
    op.create_index('ix_so_is_active', 'state_overrides', ['is_active'])

    # 1.3 event_day_zone_factors (restaurar desde P2)
    op.create_table(
        'event_day_zone_factors',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('event_day_id', sa.String(36),
                  sa.ForeignKey('event_days.id'), nullable=False),
        sa.Column('zone_type_id', sa.String(36),
                  sa.ForeignKey('zone_types.id'), nullable=False),
        sa.Column('event_state_id', sa.String(36),
                  sa.ForeignKey('event_states.id'), nullable=False),
        sa.Column('saturation_factor', sa.Float(), nullable=False),
        sa.Column('attendance_factor', sa.Float(), nullable=False),
        sa.Column('resource_factor', sa.Float(), nullable=False),
        sa.Column('priority_weight', sa.Integer(), nullable=False,
                  server_default=sa.text('50')),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),

        sa.UniqueConstraint('event_day_id', 'zone_type_id', 'event_state_id',
                            name='uq_edzf_event_day_zone_type_state'),
    )
    op.create_index('ix_edzf_event_state_id', 'event_day_zone_factors',
                    ['event_state_id'])
    op.create_index('ix_edzf_zone_type_id', 'event_day_zone_factors',
                    ['zone_type_id'])

    # ═══════════════════════════════════════════════
    # 2. RESTAURAR COLUMNAS DE event_days
    # ═══════════════════════════════════════════════

    # 2.1 Eliminar columnas nuevas
    op.drop_column('event_days', 'operational_end_min')
    op.drop_column('event_days', 'operational_start_min')
    op.drop_column('event_days', 'operational_profile_id')

    # 2.2 Recrear columnas obsoletas (nullable, sin datos)
    op.add_column('event_days', sa.Column('event_end_min', sa.Integer(),
                  nullable=True))
    op.add_column('event_days', sa.Column('exit_start_min', sa.Integer(),
                  nullable=True))
    op.add_column('event_days', sa.Column('activity_peak_end_min', sa.Integer(),
                  nullable=True))
    op.add_column('event_days', sa.Column('activity_peak_start_min', sa.Integer(),
                  nullable=True))
    op.add_column('event_days', sa.Column('entry_start_min', sa.Integer(),
                  nullable=True))

    # 2.3 Recrear CHECK constraint
    op.create_check_constraint(
        'ck_event_day_minute_order',
        'event_days',
        'entry_start_min < activity_peak_start_min AND '
        'activity_peak_start_min < activity_peak_end_min AND '
        'activity_peak_end_min < exit_start_min AND '
        'exit_start_min < event_end_min',
    )

    # ═══════════════════════════════════════════════
    # 3. ELIMINAR TABLAS NUEVAS
    # ═══════════════════════════════════════════════

    op.drop_table('operational_event_modifiers')
    op.drop_table('operational_events')
    op.drop_table('zone_behaviors')
    op.drop_table('operational_phases')
    op.drop_table('operational_profiles')


# ═══════════════════════════════════════════════
# OBSERVACIONES DEL REVISOR
# ═══════════════════════════════════════════════
#
# 1. Las columnas operational_profile_id, operational_start_min y
#    operational_end_min se definen como NOT NULL conforme a
#    P3.0_EXECUTION_SPEC.md §5.6.
#
# 2. Si existen filas en event_days antes de ejecutar esta migración,
#    se requiere un seed de migración previo que asigne valores válidos
#    a estas 3 columnas para todas las filas existentes.
#    Sin backfill, alembic upgrade head fallará con NOT NULL violation.
#
# 3. Estrategia propuesta: crear script seed_p3_migration.py que:
#    a) Cree OperationalProfiles de referencia
#    b) Asigne perfil default + ventana operativa a cada EventDay existente
#    c) Se ejecute ANTES de alembic upgrade head
#
# 4. Si event_days está vacía, el cambio a NOT NULL es seguro sin
#    pasos adicionales.
#
# 5. Ninguna otra observación detectada. El resto de la migración
#    cumple con P3.0_EXECUTION_SPEC.md §5.
