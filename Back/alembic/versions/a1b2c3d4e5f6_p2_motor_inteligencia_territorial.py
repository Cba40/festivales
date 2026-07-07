"""P2 — Motor de Inteligencia Territorial

Tablas del motor heurístico + migración de event_days a timeline TIME.

Revision ID: a1b2c3d4e5f6
Revises: 0f9f11bbb377
Create Date: 2026-07-04 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '0f9f11bbb377'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ──────────────────────────────────────────────
# UUIDs fijos para seed data (reproducibles)
# ──────────────────────────────────────────────

_EVENT_STATE_IDS = {
    'pre_apertura': 'a1111111-1111-1111-1111-111111111111',
    'temprano':     'a2222222-2222-2222-2222-222222222222',
    'pico':         'a3333333-3333-3333-3333-333333333333',
    'cierre':       'a4444444-4444-4444-4444-444444444444',
    'post_evento':  'a5555555-5555-5555-5555-555555555555',
}

_ZONE_TYPE_IDS = {
    'puesto_comida': 'b1111111-1111-1111-1111-111111111111',
    'bano':          'b2222222-2222-2222-2222-222222222222',
    'emergencia':    'b3333333-3333-3333-3333-333333333333',
    'hidratacion':   'b4444444-4444-4444-4444-444444444444',
    'ingreso':       'b5555555-5555-5555-5555-555555555555',
    'escenario':     'b6666666-6666-6666-6666-666666666666',
}


def upgrade() -> None:
    # ═══════════════════════════════════════════
    # 1. TABLAS NUEVAS
    # ═══════════════════════════════════════════

    # ── 1.1 EventState ────────────────────────
    op.create_table(
        'event_states',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('event_id', sa.String(36), sa.ForeignKey('events.id'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('color', sa.String(7), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('is_initial', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_final', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('rules', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.UniqueConstraint('event_id', 'slug', name='uq_event_states_event_slug'),
    )

    # ── 1.2 ZoneType ──────────────────────────
    op.create_table(
        'zone_types',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('icon', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('default_factors', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── 1.3 EventDayZoneFactor ────────────────
    op.create_table(
        'event_day_zone_factors',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('event_day_id', sa.String(36), sa.ForeignKey('event_days.id'), nullable=False),
        sa.Column('zone_type_id', sa.String(36), sa.ForeignKey('zone_types.id'), nullable=False),
        sa.Column('event_state_id', sa.String(36), sa.ForeignKey('event_states.id'), nullable=False),
        sa.Column('saturation_factor', sa.Float(), nullable=False),
        sa.Column('attendance_factor', sa.Float(), nullable=False),
        sa.Column('resource_factor', sa.Float(), nullable=False),
        sa.Column('priority_weight', sa.Integer(), nullable=False, server_default=sa.text('50')),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),

        sa.UniqueConstraint(
            'event_day_id', 'zone_type_id', 'event_state_id',
            name='uq_edzf_event_day_zone_type_state',
        ),
    )

    # ── 1.4 StateOverride ─────────────────────
    op.create_table(
        'state_overrides',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('event_day_id', sa.String(36), sa.ForeignKey('event_days.id'), nullable=False),
        sa.Column('event_state_id', sa.String(36), sa.ForeignKey('event_states.id'), nullable=False),
        sa.Column('zone_type_id', sa.String(36), sa.ForeignKey('zone_types.id'), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_by', sa.String(100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── 1.5 IncidentImpact ────────────────────
    op.create_table(
        'incident_impacts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('incident_id', sa.String(36), sa.ForeignKey('incidents.id'), nullable=False),
        sa.Column('zone_type_id', sa.String(36), sa.ForeignKey('zone_types.id'), nullable=False),
        sa.Column('saturation_delta', sa.Float(), nullable=False),
        sa.Column('attendance_delta', sa.Float(), nullable=False),
        sa.Column('resource_delta', sa.Float(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── 1.6 Índices adicionales ───────────────
    op.create_index('ix_edzf_event_state_id', 'event_day_zone_factors', ['event_state_id'])
    op.create_index('ix_edzf_zone_type_id', 'event_day_zone_factors', ['zone_type_id'])
    op.create_index('ix_so_event_day_timespan', 'state_overrides', ['event_day_id', 'start_time', 'end_time'])
    op.create_index('ix_so_is_active', 'state_overrides', ['is_active'])
    op.create_index('ix_ii_incident_id', 'incident_impacts', ['incident_id'])
    op.create_index('ix_ii_zone_type_id', 'incident_impacts', ['zone_type_id'])
    op.create_index('ix_event_days_event_active', 'event_days', ['event_id', 'is_active'],
                    postgresql_where=sa.text('is_active = true'))

    # ═══════════════════════════════════════════
    # 2. MIGRACIÓN DE event_days
    # ═══════════════════════════════════════════

    # 2.1 Agregar 7 columnas TIME como nullable
    op.add_column('event_days', sa.Column('entry_start_time', sa.Time(), nullable=True))
    op.add_column('event_days', sa.Column('entry_peak_start_time', sa.Time(), nullable=True))
    op.add_column('event_days', sa.Column('entry_peak_end_time', sa.Time(), nullable=True))
    op.add_column('event_days', sa.Column('event_start_time', sa.Time(), nullable=True))
    op.add_column('event_days', sa.Column('exit_peak_start_time', sa.Time(), nullable=True))
    op.add_column('event_days', sa.Column('exit_peak_end_time', sa.Time(), nullable=True))
    op.add_column('event_days', sa.Column('event_end_time', sa.Time(), nullable=True))

    # 2.2 Migrar datos existentes (best-effort mapping)
    #     opening_time       → entry_start_time (+ event_start_time = entrada+4h)
    #     peak_hour_start    → entry_peak_start_time
    #     peak_hour_end      → entry_peak_end_time
    #     closing_time       → exit_peak_start_time (+ exit_peak_end_time / event_end_time)
    #
    #     Si no hay datos viejos se asignan defaults: 16:00 – 01:00.
    #
    #     CORRECCIÓN CASO BORDE (P2.1.1): Cuando opening_time IS NOT NULL y opening_time + 4
    #     resulta igual a peak_hour_end, event_start_time e entry_peak_end_time pueden
    #     tener el mismo valor TIME (ej: opening_time=16, peak_hour_end=20 → ambos 20:00).
    #     Esto viola el constraint estricto (<). Se usa GREATEST con INTERVAL '1 minute'
    #     para garantizar event_start_time > entry_peak_end_time siempre.
    #
    #     Datos nuevos en columnas TIME se pierden en downgrade.
    op.execute("""
        UPDATE event_days SET
            entry_start_time =
                CASE WHEN opening_time IS NOT NULL
                     THEN make_time(opening_time, 0, 0) ELSE make_time(16, 0, 0) END,

            entry_peak_start_time =
                CASE WHEN peak_hour_start IS NOT NULL
                     THEN make_time(peak_hour_start, 0, 0) ELSE make_time(18, 0, 0) END,

            entry_peak_end_time =
                CASE WHEN peak_hour_end IS NOT NULL
                     THEN make_time(peak_hour_end, 0, 0) ELSE make_time(20, 0, 0) END,

            event_start_time =
                CASE WHEN opening_time IS NOT NULL
                     THEN GREATEST(
                          make_time(LEAST(opening_time + 4, 23), 0, 0),
                          (CASE WHEN peak_hour_end IS NOT NULL
                                THEN make_time(peak_hour_end, 0, 0)
                                ELSE make_time(20, 0, 0) END) + INTERVAL '1 minute'
                        )
                     ELSE make_time(20, 1, 0) END,

            exit_peak_start_time =
                CASE WHEN closing_time IS NOT NULL
                     THEN make_time(closing_time, 0, 0) ELSE make_time(23, 0, 0) END,

            exit_peak_end_time =
                CASE WHEN closing_time IS NOT NULL
                     THEN make_time((closing_time + 1) % 24, 0, 0) ELSE make_time(0, 0, 0) END,

            event_end_time =
                CASE WHEN closing_time IS NOT NULL
                     THEN make_time((closing_time + 1) % 24, 0, 0) ELSE make_time(1, 0, 0) END
    """)

    # 2.3 Set NOT NULL
    op.alter_column('event_days', 'entry_start_time', nullable=False)
    op.alter_column('event_days', 'entry_peak_start_time', nullable=False)
    op.alter_column('event_days', 'entry_peak_end_time', nullable=False)
    op.alter_column('event_days', 'event_start_time', nullable=False)
    op.alter_column('event_days', 'exit_peak_start_time', nullable=False)
    op.alter_column('event_days', 'exit_peak_end_time', nullable=False)
    op.alter_column('event_days', 'event_end_time', nullable=False)

    # 2.4 CHECK constraint de orden temporal estricto
    op.create_check_constraint(
        'ck_event_days_time_order',
        'event_days',
        'entry_start_time < entry_peak_start_time AND '
        'entry_peak_start_time < entry_peak_end_time AND '
        'entry_peak_end_time < event_start_time AND '
        'event_start_time < exit_peak_start_time AND '
        'exit_peak_start_time < exit_peak_end_time AND '
        'exit_peak_end_time < event_end_time'
    )

    # 2.5 Drop columnas viejas
    op.drop_column('event_days', 'peak_hour_start')
    op.drop_column('event_days', 'peak_hour_end')
    op.drop_column('event_days', 'opening_time')
    op.drop_column('event_days', 'closing_time')

    # ═══════════════════════════════════════════
    # 3. SEED DATA
    # ═══════════════════════════════════════════

    # 3.1 event_states (globales, event_id = NULL)
    op.execute("""
        INSERT INTO event_states
            (id, event_id, name, slug, sort_order, color, description,
             is_initial, is_final, rules, created_at)
        VALUES
        ('{pre_id}', NULL, 'Pre-apertura', 'pre_apertura', 0, '#94a3b8',
         'Apertura de puertas. El p\xfablico comienza a ingresar pero sin aglomeraciones.',
         True, False,
         '{{"tipo": "horario", "campo_inicio": null, "campo_fin": "entry_peak_start_time"}}'::jsonb,
         now()),

        ('{tem_id}', NULL, 'Temprano', 'temprano', 1, '#3b82f6',
         'Pico de ingreso. Mayor caudal de personas entrando al predio.',
         False, False,
         '{{"tipo": "horario", "campo_inicio": "entry_peak_start_time", "campo_fin": "event_start_time"}}'::jsonb,
         now()),

        ('{pico_id}', NULL, 'Pico', 'pico', 2, '#ef4444',
         'Show principal en curso. M\xe1xima concentraci\xf3n de p\xfablico en el evento.',
         False, False,
         '{{"tipo": "horario", "campo_inicio": "event_start_time", "campo_fin": "exit_peak_start_time"}}'::jsonb,
         now()),

        ('{cier_id}', NULL, 'Cierre', 'cierre', 3, '#f59e0b',
         'Pico de salida. El p\xfablico comienza a retirarse masivamente.',
         False, False,
         '{{"tipo": "horario", "campo_inicio": "exit_peak_start_time", "campo_fin": "event_end_time"}}'::jsonb,
         now()),

        ('{post_id}', NULL, 'Post-evento', 'post_evento', 4, '#6366f1',
         'Jornada finalizada. Solo personal de limpieza y log\xedstica.',
         False, True,
         '{{"tipo": "horario", "campo_inicio": "event_end_time", "campo_fin": null}}'::jsonb,
         now())
    """.format(
        pre_id=_EVENT_STATE_IDS['pre_apertura'],
        tem_id=_EVENT_STATE_IDS['temprano'],
        pico_id=_EVENT_STATE_IDS['pico'],
        cier_id=_EVENT_STATE_IDS['cierre'],
        post_id=_EVENT_STATE_IDS['post_evento'],
    ))

    # 3.2 zone_types
    op.execute("""
        INSERT INTO zone_types
            (id, name, slug, icon, description, default_factors, created_at)
        VALUES
        ('{zc_id}', 'Puesto de comida',   'puesto_comida', 'utensils-crossed',
         'Puestos de venta de comida y bebida.',
         $${{
           "pre_apertura": {{"saturation": 0.0, "attendance": 0.0, "resource": 0.3}},
           "temprano": {{"saturation": 0.4, "attendance": 0.5, "resource": 0.6}},
           "pico": {{"saturation": 1.2, "attendance": 1.5, "resource": 1.0}},
           "cierre": {{"saturation": 0.8, "attendance": 0.6, "resource": 0.5}},
           "post_evento": {{"saturation": 0.2, "attendance": 0.1, "resource": 0.2}}
         }}$$::jsonb, now()),

        ('{zb_id}', 'Ba\xf1o',   'bano', 'toilet',
         'M\xf3dulos de ba\xf1os qu\xedmicos o sanitarios.',
         $${{
           "pre_apertura": {{"saturation": 0.0, "attendance": 0.0, "resource": 0.5}},
           "temprano": {{"saturation": 0.3, "attendance": 0.4, "resource": 0.7}},
           "pico": {{"saturation": 1.5, "attendance": 1.3, "resource": 1.2}},
           "cierre": {{"saturation": 1.0, "attendance": 0.8, "resource": 0.8}},
           "post_evento": {{"saturation": 0.5, "attendance": 0.3, "resource": 0.4}}
         }}$$::jsonb, now()),

        ('{ze_id}', 'Emergencia',   'emergencia', 'tent',
         'Puestos de primeros auxilios y emergencias m\xe9dicas.',
         $${{
           "pre_apertura": {{"saturation": 0.0, "attendance": 0.0, "resource": 1.0}},
           "temprano": {{"saturation": 0.2, "attendance": 0.3, "resource": 1.0}},
           "pico": {{"saturation": 0.8, "attendance": 0.7, "resource": 1.5}},
           "cierre": {{"saturation": 0.4, "attendance": 0.3, "resource": 1.2}},
           "post_evento": {{"saturation": 0.1, "attendance": 0.1, "resource": 0.8}}
         }}$$::jsonb, now()),

        ('{zh_id}', 'Puesto de hidrataci\xf3n',   'hidratacion', 'droplets',
         'Puntos de agua potable e hidrataci\xf3n.',
         $${{
           "pre_apertura": {{"saturation": 0.0, "attendance": 0.0, "resource": 0.4}},
           "temprano": {{"saturation": 0.5, "attendance": 0.6, "resource": 0.6}},
           "pico": {{"saturation": 1.3, "attendance": 1.4, "resource": 1.1}},
           "cierre": {{"saturation": 0.7, "attendance": 0.5, "resource": 0.5}},
           "post_evento": {{"saturation": 0.3, "attendance": 0.2, "resource": 0.3}}
         }}$$::jsonb, now()),

        ('{zi_id}', 'Ingreso / Control',   'ingreso', 'scan-eye',
         'Puestos de ingreso, control de acceso y revisi\xf3n.',
         $${{
           "pre_apertura": {{"saturation": 1.5, "attendance": 1.8, "resource": 1.5}},
           "temprano": {{"saturation": 1.2, "attendance": 1.5, "resource": 1.2}},
           "pico": {{"saturation": 0.3, "attendance": 0.4, "resource": 0.6}},
           "cierre": {{"saturation": 0.1, "attendance": 0.2, "resource": 0.4}},
           "post_evento": {{"saturation": 0.0, "attendance": 0.0, "resource": 0.2}}
         }}$$::jsonb, now()),

        ('{zest_id}', 'Escenario',   'escenario', 'stage',
         'Zona del escenario principal y \xe1reas aleda\xf1as.',
         $${{
           "pre_apertura": {{"saturation": 0.0, "attendance": 0.0, "resource": 0.5}},
           "temprano": {{"saturation": 0.6, "attendance": 0.8, "resource": 0.7}},
           "pico": {{"saturation": 1.8, "attendance": 2.0, "resource": 1.5}},
           "cierre": {{"saturation": 0.5, "attendance": 0.4, "resource": 1.0}},
           "post_evento": {{"saturation": 0.1, "attendance": 0.1, "resource": 0.3}}
         }}$$::jsonb, now())
    """.format(
        zc_id=_ZONE_TYPE_IDS['puesto_comida'],
        zb_id=_ZONE_TYPE_IDS['bano'],
        ze_id=_ZONE_TYPE_IDS['emergencia'],
        zh_id=_ZONE_TYPE_IDS['hidratacion'],
        zi_id=_ZONE_TYPE_IDS['ingreso'],
        zest_id=_ZONE_TYPE_IDS['escenario'],
    ))


def downgrade() -> None:
    # ═══════════════════════════════════════════
    # 1. ELIMINAR SEED DATA
    # ═══════════════════════════════════════════
    op.execute("DELETE FROM zone_types")
    op.execute("DELETE FROM event_states")

    # ═══════════════════════════════════════════
    # 2. DROP TABLAS NUEVAS
    # ═══════════════════════════════════════════
    op.drop_table('incident_impacts')
    op.drop_table('state_overrides')
    op.drop_table('event_day_zone_factors')
    op.drop_table('zone_types')
    op.drop_table('event_states')

    # ═══════════════════════════════════════════
    # 3. REVERTIR event_days
    # ═══════════════════════════════════════════
    op.drop_index('ix_event_days_event_active', table_name='event_days')
    op.drop_constraint('ck_event_days_time_order', 'event_days', type_='check')

    op.drop_column('event_days', 'event_end_time')
    op.drop_column('event_days', 'exit_peak_end_time')
    op.drop_column('event_days', 'exit_peak_start_time')
    op.drop_column('event_days', 'event_start_time')
    op.drop_column('event_days', 'entry_peak_end_time')
    op.drop_column('event_days', 'entry_peak_start_time')
    op.drop_column('event_days', 'entry_start_time')

    # NOTA: Los datos originales en opening_time/closing_time/peak_hour_*
    # fueron migrados a TIME durante upgrade. Al restaurar columnas viejas
    # los valores originales no se recuperan.
    op.add_column('event_days', sa.Column('closing_time', sa.Integer(), nullable=True))
    op.add_column('event_days', sa.Column('opening_time', sa.Integer(), nullable=True))
    op.add_column('event_days', sa.Column('peak_hour_end', sa.Integer(), nullable=True))
    op.add_column('event_days', sa.Column('peak_hour_start', sa.Integer(), nullable=True))
