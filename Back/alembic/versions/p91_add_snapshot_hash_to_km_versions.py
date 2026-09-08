"""p91 — add snapshot hash and version sequence to knowledge_model_versions.

Revision ID: p91
Revises: p80
Create Date: 2026-09-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'p91'
down_revision: Union[str, Sequence[str], None] = 'p80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS km_version_number_seq")

    op.add_column(
        'knowledge_model_versions',
        sa.Column('snapshot_hash', sa.String(length=64), nullable=True),
    )
    op.create_unique_constraint(
        'uq_km_versions_snapshot_hash',
        'knowledge_model_versions',
        ['snapshot_hash'],
    )

    op.alter_column(
        'knowledge_model_versions',
        'version_number',
        server_default=sa.text("nextval('km_version_number_seq')"),
    )


def downgrade() -> None:
    op.drop_constraint(
        'uq_km_versions_snapshot_hash',
        'knowledge_model_versions',
        type_='unique',
    )
    op.drop_column('knowledge_model_versions', 'snapshot_hash')

    op.alter_column(
        'knowledge_model_versions',
        'version_number',
        server_default=None,
    )
    op.execute("DROP SEQUENCE IF EXISTS km_version_number_seq")