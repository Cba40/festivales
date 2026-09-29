"""add corrected_by/corrected_at to operational_observations

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-09-29

Por que esta migracion esta escrita a mano y no con --autogenerate
----------------------------------------------------------------
`f2a3b4c5d6e7` documento el problema exacto: antes de corregir `env.py`,
`alembic revision --autogenerate` generaba `op.drop_table('operational_observations')`
sobre la tabla que tiene datos en Neon. El autogenerate compara el modelo contra
la base conectada: si el entorno local no tiene alguna tabla, o si la metadata
del env no esta alineada, propone operaciones destructivas que en esta tabla
concreto ya casi provocaron un borrado de 17 filas.

El requisito de esta revision es que SOLO agregue dos columnas. Eso es mas
facil de garantizar escribiendo el `upgrade()` a mano que auditando el
autogenerate despues: aca el `upgrade()` tiene exactamente dos `add_column` y
nada mas. No hay `drop_table`, `drop_column`, `alter_column` ni `create_index`.

Sobre las columnas
------------------
* `corrected_by VARCHAR(100) NULL`: nombre de quien corrigio. NULL = nunca se
  corrigio. Sin default del lado de la base a proposito: el unico escritor es el
  PATCH, y un default (por mas que sea `now()`) haria que toda fila recien
  creada pareciera corregida.
* `corrected_at TIMESTAMPTZ NULL`: igual criterio. Se escribe en la misma
  sentencia que `corrected_by`, para que no exista el estado imposible
  "corregida sin fecha" ni "fecha sin autor".

No se toca ninguna columna existente: `observed_density`, `timestamp`, `zone_id`,
`event_day_id` y `metadata` quedan intactos. La edicion in-place de
`observed_density` (PATCH) no requiere backfill ni default: las filas previas
tienen NULL en ambas columnas y eso significa "sin corregir", que es lo correcto.

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-09-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4c5d6e7f8a9'
down_revision: Union[str, Sequence[str], None] = 'a3b4c5d6e7f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'operational_observations',
        sa.Column('corrected_by', sa.String(length=100), nullable=True),
    )
    op.add_column(
        'operational_observations',
        sa.Column('corrected_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('operational_observations', 'corrected_at')
    op.drop_column('operational_observations', 'corrected_by')
