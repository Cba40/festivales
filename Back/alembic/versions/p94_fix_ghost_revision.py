"""p94 — ghost revision to reconcile orphaned alembic_version entries.

Varias bases (desarrollo local / Neon) tienen `alembic_version = 'p94'` en la
tabla `alembic_version`, pero ninguna migración con ese id existe en el repo.

Este archivo declara dicha revisión (sin operaciones) para que Alembic pueda
resolver la cadena `p93 -> p94 -> e4e6a8c1f2b3 -> f5f7b8d0e1c2` y continuar el
upgrade. No modifica ninguna tabla ni dato.

Revision ID: p94
Revises: p93
Create Date: 2026-09-21
"""

from typing import Sequence, Union

from alembic import op  # noqa: F401


revision: str = 'p94'
down_revision: Union[str, Sequence[str], None] = 'p93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass