"""average_parking_duration

Agrega la columna nullable `event_days.average_parking_duration` (Float).

Tiempo promedio, expresado en horas, que un vehículo permanece estacionado
durante el evento. Hipótesis inicial de modelado (4 h), calibrable.

Revision ID: b3c2d1a0f9e8
Revises: a2b1c0d9e8f7
Create Date: 2026-08-10 12:07:07.331665

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3c2d1a0f9e8'
down_revision: Union[str, Sequence[str], None] = 'a2b1c0d9e8f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega event_days.average_parking_duration (Float, nullable)."""
    op.add_column(
        'event_days',
        sa.Column('average_parking_duration', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    """Elimina únicamente event_days.average_parking_duration."""
    op.drop_column('event_days', 'average_parking_duration')
