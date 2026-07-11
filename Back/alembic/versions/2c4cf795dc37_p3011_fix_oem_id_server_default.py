"""p3011_fix_oem_id_server_default

Revision ID: 2c4cf795dc37
Revises: d0e1f2a3b4c5
Create Date: 2026-07-10 21:24:51.746045

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c4cf795dc37'
down_revision: Union[str, Sequence[str], None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'operational_event_modifiers', 'id',
        server_default=sa.text('gen_random_uuid()'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'operational_event_modifiers', 'id',
        server_default=None,
    )
