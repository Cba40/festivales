"""estimated_vehicles_column

Agrega la columna nullable `event_days.estimated_vehicles` (Integer).

Cantidad estimada de vehículos asociados al evento que se espera que ingresen
al territorio durante ese día. Magnitud independiente de estimated_attendance /
AttendanceLevel.

Revision ID: a2b1c0d9e8f7
Revises: f7a1c9d0e1b2
Create Date: 2026-08-10 09:51:06.081459

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2b1c0d9e8f7'
down_revision: Union[str, Sequence[str], None] = 'f7a1c9d0e1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Agrega event_days.estimated_vehicles (Integer, nullable)."""
    op.add_column(
        'event_days',
        sa.Column('estimated_vehicles', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Elimina únicamente event_days.estimated_vehicles."""
    op.drop_column('event_days', 'estimated_vehicles')
