"""P2.0.1 — Refactor temporal: minutos relativos + AttendanceLevel

- Elimina columnas TIME de event_days, agrega INT minutos
- Crea tabla attendance_levels
- StateOverride: start_time/end_time (datetime) → start_min/end_min (int)
- EventState.rules: tipo "horario" → "minutos"
- Elimina función check_event_day_time_order

Revision ID: c0d1e2f3a4b5
Revises: b2c3d4e5f6a7
Create Date: 2026-07-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c0d1e2f3a4b5'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EVENT_STATE_IDS = {
    'pre_apertura': 'a1111111-1111-1111-1111-111111111111',
    'temprano':     'a2222222-2222-2222-2222-222222222222',
    'pico':         'a3333333-3333-3333-3333-333333333333',
    'cierre':       'a4444444-4444-4444-4444-444444444444',
    'post_evento':  'a5555555-5555-5555-5555-555555555555',
}


def upgrade() -> None:
    # ═══════════════════════════════════════════
    # 1. EVENT_DAYS — migración TIME → INT
    # ═══════════════════════════════════════════

    # 1.1 Agregar columnas INT como nullable
    op.add_column('event_days', sa.Column('entry_start_min', sa.Integer(), nullable=True))
    op.add_column('event_days', sa.Column('activity_peak_start_min', sa.Integer(), nullable=True))
    op.add_column('event_days', sa.Column('activity_peak_end_min', sa.Integer(), nullable=True))
    op.add_column('event_days', sa.Column('exit_start_min', sa.Integer(), nullable=True))
    op.add_column('event_days', sa.Column('event_end_min', sa.Integer(), nullable=True))
    op.add_column('event_days', sa.Column('estimated_attendance', sa.Integer(), nullable=True))

    # 1.2 Migrar datos: TIME → minutos desde medianoche
    op.execute("""
        UPDATE event_days SET
            entry_start_min =
                EXTRACT(HOUR FROM entry_start_time) * 60 + EXTRACT(MINUTE FROM entry_start_time),
            activity_peak_start_min =
                EXTRACT(HOUR FROM entry_peak_start_time) * 60 + EXTRACT(MINUTE FROM entry_peak_start_time),
            activity_peak_end_min =
                EXTRACT(HOUR FROM entry_peak_end_time) * 60 + EXTRACT(MINUTE FROM entry_peak_end_time),
            exit_start_min =
                EXTRACT(HOUR FROM exit_peak_start_time) * 60 + EXTRACT(MINUTE FROM exit_peak_start_time),
            event_end_min =
                EXTRACT(HOUR FROM event_end_time) * 60 + EXTRACT(MINUTE FROM event_end_time),
            estimated_attendance = COALESCE(expected_attendance, 0)
    """)

    # 1.3 Set NOT NULL
    op.alter_column('event_days', 'entry_start_min', nullable=False)
    op.alter_column('event_days', 'activity_peak_start_min', nullable=False)
    op.alter_column('event_days', 'activity_peak_end_min', nullable=False)
    op.alter_column('event_days', 'exit_start_min', nullable=False)
    op.alter_column('event_days', 'event_end_min', nullable=False)
    op.alter_column('event_days', 'estimated_attendance', nullable=False)

    # 1.4 Agregar CHECK constraint de orden temporal (minutos)
    op.create_check_constraint(
        'ck_event_day_minute_order',
        'event_days',
        'entry_start_min < activity_peak_start_min AND '
        'activity_peak_start_min < activity_peak_end_min AND '
        'activity_peak_end_min < exit_start_min AND '
        'exit_start_min < event_end_min'
    )

    # 1.5 Drop columnas TIME viejas
    op.drop_constraint('ck_event_days_time_order', 'event_days', type_='check')
    op.drop_column('event_days', 'entry_start_time')
    op.drop_column('event_days', 'entry_peak_start_time')
    op.drop_column('event_days', 'entry_peak_end_time')
    op.drop_column('event_days', 'event_start_time')
    op.drop_column('event_days', 'exit_peak_start_time')
    op.drop_column('event_days', 'exit_peak_end_time')
    op.drop_column('event_days', 'event_end_time')
    op.drop_column('event_days', 'expected_attendance')

    # 1.6 Drop función vieja (ya no se usa)
    op.execute("DROP FUNCTION IF EXISTS check_event_day_time_order")

    # ═══════════════════════════════════════════
    # 2. ATTENDANCE_LEVELS — tabla nueva
    # ═══════════════════════════════════════════
    op.create_table(
        'attendance_levels',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('event_id', sa.String(36), sa.ForeignKey('events.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('min_people', sa.Integer(), nullable=False),
        sa.Column('max_people', sa.Integer(), nullable=True),
        sa.Column('global_multiplier', sa.Float(), nullable=False),

        sa.UniqueConstraint('event_id', 'name', name='uq_attendance_level_event_name'),
        sa.UniqueConstraint('event_id', 'min_people', 'max_people', name='uq_attendance_level_range'),
    )

    # ═══════════════════════════════════════════
    # 3. STATE_OVERRIDES — datetime → int
    # ═══════════════════════════════════════════
    # 3.1 Agregar columnas INT como nullable
    op.add_column('state_overrides', sa.Column('start_min', sa.Integer(), nullable=True))
    op.add_column('state_overrides', sa.Column('end_min', sa.Integer(), nullable=True))

    # 3.2 No hay datos reales; setear valores por defecto seguros
    op.execute("UPDATE state_overrides SET start_min = 0, end_min = 0")

    # 3.3 Set NOT NULL
    op.alter_column('state_overrides', 'start_min', nullable=False)
    op.alter_column('state_overrides', 'end_min', nullable=False)

    # 3.4 Drop columnas datetime viejas
    op.execute("DROP INDEX IF EXISTS ix_so_event_day_timespan")
    op.execute("DROP INDEX IF EXISTS ix_state_override_event_day_times")
    op.drop_column('state_overrides', 'start_time')
    op.drop_column('state_overrides', 'end_time')

    # 3.5 Crear índice nuevo sobre minutos
    op.create_index(
        'ix_state_override_event_day_minutes',
        'state_overrides',
        ['event_day_id', 'start_min', 'end_min'],
    )

    # ═══════════════════════════════════════════
    # 4. EVENT_STATES — actualizar reglas a "minutos"
    # ═══════════════════════════════════════════
    op.execute(f"""
        UPDATE event_states SET rules = '{{"tipo": "minutos", "campo_inicio": null, "campo_fin": "activity_peak_start_min"}}'::jsonb
        WHERE id = '{_EVENT_STATE_IDS['pre_apertura']}'
    """)
    op.execute(f"""
        UPDATE event_states SET rules = '{{"tipo": "minutos", "campo_inicio": "activity_peak_start_min", "campo_fin": "activity_peak_end_min"}}'::jsonb
        WHERE id = '{_EVENT_STATE_IDS['temprano']}'
    """)
    op.execute(f"""
        UPDATE event_states SET rules = '{{"tipo": "minutos", "campo_inicio": "activity_peak_end_min", "campo_fin": "exit_start_min"}}'::jsonb
        WHERE id = '{_EVENT_STATE_IDS['pico']}'
    """)
    op.execute(f"""
        UPDATE event_states SET rules = '{{"tipo": "minutos", "campo_inicio": "exit_start_min", "campo_fin": "event_end_min"}}'::jsonb
        WHERE id = '{_EVENT_STATE_IDS['cierre']}'
    """)
    op.execute(f"""
        UPDATE event_states SET rules = '{{"tipo": "minutos", "campo_inicio": "event_end_min", "campo_fin": null}}'::jsonb
        WHERE id = '{_EVENT_STATE_IDS['post_evento']}'
    """)


def downgrade() -> None:
    # ═══════════════════════════════════════════
    # 1. STATE_OVERRIDES — revertir int → datetime
    # ═══════════════════════════════════════════
    op.drop_index('ix_state_override_event_day_minutes', table_name='state_overrides')

    op.add_column('state_overrides', sa.Column('end_time', sa.DateTime(timezone=True), nullable=True))
    op.add_column('state_overrides', sa.Column('start_time', sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE state_overrides SET start_time = now(), end_time = now()")

    op.alter_column('state_overrides', 'start_time', nullable=False)
    op.alter_column('state_overrides', 'end_time', nullable=False)

    op.drop_column('state_overrides', 'end_min')
    op.drop_column('state_overrides', 'start_min')

    op.create_index('ix_so_event_day_timespan', 'state_overrides', ['event_day_id', 'start_time', 'end_time'])

    # ═══════════════════════════════════════════
    # 2. ATTENDANCE_LEVELS — drop table
    # ═══════════════════════════════════════════
    op.drop_table('attendance_levels')

    # ═══════════════════════════════════════════
    # 3. EVENT_DAYS — revertir INT → TIME
    # ═══════════════════════════════════════════
    op.drop_constraint('ck_event_day_minute_order', 'event_days', type_='check')

    op.add_column('event_days', sa.Column('expected_attendance', sa.Integer(), nullable=True))
    op.add_column('event_days', sa.Column('event_end_time', sa.Time(), nullable=True))
    op.add_column('event_days', sa.Column('exit_peak_end_time', sa.Time(), nullable=True))
    op.add_column('event_days', sa.Column('exit_peak_start_time', sa.Time(), nullable=True))
    op.add_column('event_days', sa.Column('event_start_time', sa.Time(), nullable=True))
    op.add_column('event_days', sa.Column('entry_peak_end_time', sa.Time(), nullable=True))
    op.add_column('event_days', sa.Column('entry_peak_start_time', sa.Time(), nullable=True))
    op.add_column('event_days', sa.Column('entry_start_time', sa.Time(), nullable=True))

    op.execute("""
        UPDATE event_days SET
            entry_start_time = make_time(entry_start_min / 60, entry_start_min % 60, 0),
            entry_peak_start_time = make_time(activity_peak_start_min / 60, activity_peak_start_min % 60, 0),
            entry_peak_end_time = make_time(activity_peak_end_min / 60, activity_peak_end_min % 60, 0),
            event_start_time = make_time(activity_peak_end_min / 60, activity_peak_end_min % 60, 0),
            exit_peak_start_time = make_time(exit_start_min / 60, exit_start_min % 60, 0),
            exit_peak_end_time = make_time(event_end_min / 60, event_end_min % 60, 0),
            event_end_time = make_time(event_end_min / 60, event_end_min % 60, 0),
            expected_attendance = estimated_attendance
    """)

    op.alter_column('event_days', 'entry_start_time', nullable=False)
    op.alter_column('event_days', 'entry_peak_start_time', nullable=False)
    op.alter_column('event_days', 'entry_peak_end_time', nullable=False)
    op.alter_column('event_days', 'event_start_time', nullable=False)
    op.alter_column('event_days', 'exit_peak_start_time', nullable=False)
    op.alter_column('event_days', 'exit_peak_end_time', nullable=False)
    op.alter_column('event_days', 'event_end_time', nullable=False)

    op.drop_column('event_days', 'estimated_attendance')
    op.drop_column('event_days', 'event_end_min')
    op.drop_column('event_days', 'exit_start_min')
    op.drop_column('event_days', 'activity_peak_end_min')
    op.drop_column('event_days', 'activity_peak_start_min')
    op.drop_column('event_days', 'entry_start_min')

    # ═══════════════════════════════════════════
    # 4. EVENT_STATES — revertir reglas a "horario"
    # ═══════════════════════════════════════════
    op.execute(f"""
        UPDATE event_states SET rules = '{{"tipo": "horario", "campo_inicio": null, "campo_fin": "entry_peak_start_time"}}'::jsonb
        WHERE id = '{_EVENT_STATE_IDS['pre_apertura']}'
    """)
    op.execute(f"""
        UPDATE event_states SET rules = '{{"tipo": "horario", "campo_inicio": "entry_peak_start_time", "campo_fin": "event_start_time"}}'::jsonb
        WHERE id = '{_EVENT_STATE_IDS['temprano']}'
    """)
    op.execute(f"""
        UPDATE event_states SET rules = '{{"tipo": "horario", "campo_inicio": "event_start_time", "campo_fin": "exit_peak_start_time"}}'::jsonb
        WHERE id = '{_EVENT_STATE_IDS['pico']}'
    """)
    op.execute(f"""
        UPDATE event_states SET rules = '{{"tipo": "horario", "campo_inicio": "exit_peak_start_time", "campo_fin": "event_end_time"}}'::jsonb
        WHERE id = '{_EVENT_STATE_IDS['cierre']}'
    """)
    op.execute(f"""
        UPDATE event_states SET rules = '{{"tipo": "horario", "campo_inicio": "event_end_time", "campo_fin": null}}'::jsonb
        WHERE id = '{_EVENT_STATE_IDS['post_evento']}'
    """)
