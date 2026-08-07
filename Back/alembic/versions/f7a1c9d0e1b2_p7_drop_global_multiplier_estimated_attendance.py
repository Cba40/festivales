"""P7 — Desacoplar intensidad global de AttendanceLevel

Sprint P7:
  - Elimina attendance_levels.global_multiplier (la intensidad ahora es por fase
    en event_day_phases.intensity).
  - Elimina event_days.estimated_attendance (la concurrencia del día queda
    representada únicamente por AttendanceLevel).

Revision ID: f3a1c9d0e1b2
Revises: f0e1d2c3b4a5
Create Date: 2026-08-07

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f7a1c9d0e1b2'
down_revision: Union[str, Sequence[str], None] = 'c6d7e8f9a0b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # La intensidad global deja de existir; la intensidad vive por fase.
    op.drop_column('attendance_levels', 'global_multiplier')

    # La concurrencia del día se representa mediante AttendanceLevel.
    op.drop_column('event_days', 'estimated_attendance')


def downgrade() -> None:
    # Reagregar columnas (reversible; los valores de intensidad global no
    # pueden recuperarse, se reinsertan como nullable para no romper).
    op.add_column(
        'attendance_levels',
        sa.Column('global_multiplier', sa.Float(), nullable=True),
    )
    op.add_column(
        'event_days',
        sa.Column('estimated_attendance', sa.Integer(), nullable=True),
    )