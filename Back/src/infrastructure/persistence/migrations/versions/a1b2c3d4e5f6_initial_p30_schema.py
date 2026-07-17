"""P3.0 — Initial schema: all domain tables.

Creates the 10 P3.0 tables defined in P3.0_EXECUTION_SPEC.md §2.1:
zone_types, zones, operational_profiles, operational_phases,
zone_behaviors, attendance_levels, event_days, event_day_phases,
operational_events, predictions.

Revision ID: a1b2c3d4e5f6
Revises: None
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ─── 1. zone_types (§2.1) ──────────────────────────────────────────────
    op.create_table(
        'zone_types',
        sa.Column('id', sa.UUID(), primary_key=True,
                   server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
    )

    # ─── 2. zones (§2.1) ───────────────────────────────────────────────────
    op.create_table(
        'zones',
        sa.Column('id', sa.UUID(), primary_key=True,
                   server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('zone_type_id', sa.UUID(),
                   sa.ForeignKey('zone_types.id'), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
    )
    op.create_check_constraint(
        'ck_zones_capacity_positive', 'zones',
        sa.text('capacity > 0'),
    )

    # ─── 3. operational_profiles (§2.1) ────────────────────────────────────
    op.create_table(
        'operational_profiles',
        sa.Column('id', sa.UUID(), primary_key=True,
                   server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
    )

    # ─── 4. operational_phases (§2.1) ──────────────────────────────────────
    op.create_table(
        'operational_phases',
        sa.Column('id', sa.UUID(), primary_key=True,
                   server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('operational_profile_id', sa.UUID(),
                   sa.ForeignKey('operational_profiles.id'), nullable=False),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),

        sa.UniqueConstraint('operational_profile_id', 'sequence_order',
                            name='uq_operational_phases_profile_seq'),
    )
    op.create_check_constraint(
        'ck_operational_phases_sequence_order_positive', 'operational_phases',
        sa.text('sequence_order > 0'),
    )

    # ─── 5. zone_behaviors (§2.1) ──────────────────────────────────────────
    op.create_table(
        'zone_behaviors',
        sa.Column('id', sa.UUID(), primary_key=True,
                   server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('operational_phase_id', sa.UUID(),
                   sa.ForeignKey('operational_phases.id'), nullable=False),
        sa.Column('zone_type_id', sa.UUID(),
                   sa.ForeignKey('zone_types.id'), nullable=False),
        sa.Column('density_factor', sa.Float(), nullable=False),
        sa.Column('flow_restriction',
                   sa.Enum('OPEN', 'REGULATED', 'CLOSED', name='flowrestriction'),
                   nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),

        sa.UniqueConstraint('operational_phase_id', 'zone_type_id',
                            name='uq_zone_behaviors_phase_zone_type'),
    )
    op.create_check_constraint(
        'ck_zone_behaviors_density_factor_range', 'zone_behaviors',
        sa.text('density_factor >= 0.0 AND density_factor <= 1.0'),
    )

    # ─── 6. attendance_levels (§2.1) ───────────────────────────────────────
    op.create_table(
        'attendance_levels',
        sa.Column('id', sa.UUID(), primary_key=True,
                   server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('multiplier', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
    )
    op.create_check_constraint(
        'ck_attendance_levels_multiplier_range', 'attendance_levels',
        sa.text('multiplier >= 0.1 AND multiplier <= 2.0'),
    )

    # ─── 7. event_days (§2.1) ──────────────────────────────────────────────
    op.create_table(
        'event_days',
        sa.Column('id', sa.UUID(), primary_key=True,
                   server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('operational_profile_id', sa.UUID(),
                   sa.ForeignKey('operational_profiles.id'), nullable=False),
        sa.Column('attendance_level_id', sa.UUID(),
                   sa.ForeignKey('attendance_levels.id'), nullable=False),
        sa.Column('operational_start_min', sa.Integer(), nullable=False),
        sa.Column('operational_end_min', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
    )
    op.create_check_constraint(
        'ck_event_days_operational_start_min_non_negative', 'event_days',
        sa.text('operational_start_min >= 0'),
    )
    op.create_check_constraint(
        'ck_event_days_operational_end_min_gt_start', 'event_days',
        sa.text('operational_end_min > operational_start_min'),
    )

    # ─── 8. event_day_phases (§2.1) ────────────────────────────────────────
    op.create_table(
        'event_day_phases',
        sa.Column('id', sa.UUID(), primary_key=True,
                   server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('event_day_id', sa.UUID(),
                   sa.ForeignKey('event_days.id'), nullable=False),
        sa.Column('operational_phase_id', sa.UUID(),
                   sa.ForeignKey('operational_phases.id'), nullable=False),
        sa.Column('start_min', sa.Integer(), nullable=False),
        sa.Column('end_min', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
    )
    op.create_check_constraint(
        'ck_event_day_phases_start_min_non_negative', 'event_day_phases',
        sa.text('start_min >= 0'),
    )
    op.create_check_constraint(
        'ck_event_day_phases_end_min_gt_start_min', 'event_day_phases',
        sa.text('end_min > start_min'),
    )

    # ─── 9. operational_events (§2.1) ──────────────────────────────────────
    op.create_table(
        'operational_events',
        sa.Column('id', sa.UUID(), primary_key=True,
                   server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('target_zone_id', sa.UUID(),
                   sa.ForeignKey('zones.id'), nullable=False),
        sa.Column('impact_value', sa.Integer(), nullable=False),
        sa.Column('is_incident', sa.Boolean(), nullable=False),
        sa.Column('start_timestamp', sa.DateTime(), nullable=False),
        sa.Column('end_timestamp', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
    )
    op.create_check_constraint(
        'ck_operational_events_impact_value_range', 'operational_events',
        sa.text('impact_value >= -100 AND impact_value <= 100'),
    )
    op.create_check_constraint(
        'ck_operational_events_end_gt_start', 'operational_events',
        sa.text('end_timestamp > start_timestamp'),
    )

    # ─── 10. predictions (§2.2 / RFC-004 §4.2) ─────────────────────────────
    op.create_table(
        'predictions',
        sa.Column('id', sa.UUID(), primary_key=True,
                   server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, unique=True),
        sa.Column('active_phase_id', sa.UUID(), nullable=False),
        sa.Column('active_event_day_phase_id', sa.UUID(), nullable=False),
        sa.Column('zone_states_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                   server_default=sa.func.now()),
    )
    op.create_unique_constraint('uq_predictions_timestamp', 'predictions', ['timestamp'])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table('predictions')
    op.drop_table('operational_events')
    op.drop_table('event_day_phases')
    op.drop_table('event_days')
    op.drop_table('attendance_levels')
    op.drop_table('zone_behaviors')
    op.drop_table('operational_phases')
    op.drop_table('operational_profiles')
    op.drop_table('zones')
    op.drop_table('zone_types')

    # Drop enum type
    sa.Enum(name='flowrestriction').drop(op.get_bind())
