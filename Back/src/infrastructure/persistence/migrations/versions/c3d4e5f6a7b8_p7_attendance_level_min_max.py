"""P7 — AttendanceLevel: multiplier → rango de personas.

Sprint P7: AttendanceLevel deja de representar la intensidad global
(multiplier). Ahora representa únicamente la concurrencia estimada del día a
través del rango de personas (min_people/max_people). La intensidad operativa
es por fase (event_day_phases.intensity).

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        'ck_attendance_levels_multiplier_range',
        'attendance_levels',
        type_='check',
    )
    op.drop_column('attendance_levels', 'multiplier')

    op.add_column(
        'attendance_levels',
        sa.Column('min_people', sa.Integer(), nullable=False, server_default=sa.text('0')),
    )
    op.add_column(
        'attendance_levels',
        sa.Column('max_people', sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        'ck_attendance_levels_min_people_non_negative',
        'attendance_levels',
        sa.text('min_people >= 0'),
    )


def downgrade() -> None:
    op.drop_constraint(
        'ck_attendance_levels_min_people_non_negative',
        'attendance_levels',
        type_='check',
    )
    op.drop_column('attendance_levels', 'max_people')
    op.drop_column('attendance_levels', 'min_people')

    op.add_column(
        'attendance_levels',
        sa.Column('multiplier', sa.Float(), nullable=False, server_default=sa.text('1.0')),
    )
    op.create_check_constraint(
        'ck_attendance_levels_multiplier_range',
        'attendance_levels',
        sa.text('multiplier >= 0.1 AND multiplier <= 2.0'),
    )