"""drop legacy incidents and operational_event_modifiers tables

Revision ID: f6g7h8i9j0k1
Revises: e7f8a9b0c1d2
Create Date: 2026-09-01

Drops the legacy tables replaced by the RFC-OPERATIONAL-EVENTS-V1 flow:
incidents, incident_impacts and operational_event_modifiers.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f6g7h8i9j0k1'
down_revision: Union[str, Sequence[str], None] = 'e7f8a9b0c1d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('DROP TABLE IF EXISTS incident_impacts CASCADE')
    op.execute('DROP TABLE IF EXISTS incidents CASCADE')
    op.execute('DROP TABLE IF EXISTS operational_event_modifiers CASCADE')


def downgrade() -> None:
    # The legacy schema is intentionally not reconstructed. Re-running the
    # historical migrations (1e040f8557ec, a1b2c3d4e5f6, d0e1f2a3b4c5, ...)
    # is required to restore these tables.
    pass
