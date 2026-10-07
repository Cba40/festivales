"""merge heads before bathroom use rate

Revision ID: 437c6b0972fc
Revises: a8b9c0d1e2f3, d2a4b6c8e0f1
Create Date: 2026-10-06 23:10:00.018985

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '437c6b0972fc'
down_revision: Union[str, Sequence[str], None] = ('a8b9c0d1e2f3', 'd2a4b6c8e0f1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
