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
    # 0) Prerrequisito: la tabla tiene que existir. En Neon de produccion la
    #    creo una migracion del arbol huerfano
    #    (`src/infrastructure/persistence/migrations/versions/`, al que
    #    `alembic.ini` no apunta), asi que en este arbol jamas se creo y esta
    #    migracion fallaba con `relation "knowledge_model_versions" does not
    #    exist`. El propio repo lo admite en el docstring de f2a3b4c5d6e7.
    #
    #    Se crea en su estado HISTORICO, es decir sin `snapshot_hash` y sin el
    #    UNIQUE `uq_km_versions_snapshot_hash`: los agrega este mismo upgrade mas
    #    abajo, y crearlos aqui daria "column already exists". Por la misma
    #    razon `version_number` se crea sin el `server_default` de la secuencia;
    #    lo setea el `alter_column` de mas abajo.
    #
    #    Sin FK a proposito, igual que el modelo: `KnowledgeModelVersionModel`
    #    declara `knowledge_model_version_id` en otros lado pero no una FK.
    #    `IF NOT EXISTS` la hace no-op en una base que ya la tiene.
    op.execute(sa.text(
        """
        CREATE TABLE IF NOT EXISTS knowledge_model_versions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            version_number integer NOT NULL,
            snapshot_data JSON NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now(),
            created_by varchar(100)
        )
        """
    ))

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