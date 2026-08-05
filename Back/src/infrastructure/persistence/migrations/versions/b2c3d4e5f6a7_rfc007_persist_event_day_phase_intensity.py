"""P3.3.4.1 — Alineación de la persistencia con RFC-007.

Cambios:

event_days
  - operational_profile_id pasa a ser opcional (nullable).

event_day_phases
  - se agrega la columna intensity (Float, NOT NULL, default 1.0).

La migración es reversible y no elimina columnas ni tablas.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-05 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ``event_days.operational_profile_id`` pasa a ser opcional.
    op.alter_column(
        'event_days',
        'operational_profile_id',
        existing_type=sa.UUID(),
        nullable=True,
    )

    # ``event_day_phases.intensity`` se materializa en persistencia.
    op.add_column(
        'event_day_phases',
        sa.Column(
            'intensity',
            sa.Float(),
            nullable=False,
            server_default=sa.text('1.0'),
        ),
    )


def downgrade() -> None:
    # Revertir: quitar la columna intensity.
    op.drop_column('event_day_phases', 'intensity')

    # Restaurar NOT NULL en operational_profile_id.
    op.alter_column(
        'event_days',
        'operational_profile_id',
        existing_type=sa.UUID(),
        nullable=False,
    )