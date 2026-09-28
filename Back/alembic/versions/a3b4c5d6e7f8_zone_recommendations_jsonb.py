"""zone_recommendations: json -> jsonb en reasoning y metadata

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-09-28

Por que esta migracion existe
----------------------------
El modelo `ZoneRecommendationModel` declara `reasoning` y `metadata` como
`JSONB`, pero la columna en la base de produccion (Neon) es `json`: la creo la
revision p92 con `sa.JSON()` y nunca se bumpeo.

Decision: NO se degrada el modelo a `JSON`. `jsonb` habilita indexado GIN y los
operadores `?`, `@>`, `@@`, que `json` no tiene. Se migra la base hacia el
modelo en lugar de al revés.

Verificado en Neon (read-only):

    timestamp    timestamp with time zone
    reasoning    json
    metadata     json
    created_at   timestamp with time zone

Nota sobre `timestamp`: la columna ya era timestamptz en la base (p92 la creo
asi). El modelo era el que declaraba `DateTime` naive. Esa parte se corrige
solo en el modelo y no necesita migracion: este archivo no la toca.

Seguridad
---------
* `json` -> `jsonb` es una conversion sin perdida: todo valor que Postgres
  acepto como `json` es convertible a `jsonb`, porque el tipo `json` ya
  garantiza JSON valido. La conversion no puede fallar por datos.
* Postgres NO tiene coerccion binaria entre `json` y `jsonb`: la conversion
  reescribe la tabla entera. Por eso se fija `lock_timeout`: si otra transaccion
  tiene tomado el lock, la migracion falla rapido en vez de quedar esperando
  encolada y bloqueando escrituras. Es un guard, no un cambio de esquema.
* El `downgrade` (jsonb -> json) es simetrico y tambien sin perdida.

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-09-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

LOCK_TIMEOUT = '5s'


def _set_lock_timeout() -> None:
    # El valor de lock_timeout es un literal de texto en Postgres: va entre
    # comillas. LOCK_TIMEOUT es una constante de este archivo, no input externo.
    op.execute(sa.text(f"SET LOCAL lock_timeout = '{LOCK_TIMEOUT}'"))


def upgrade() -> None:
    # json -> jsonb reescribe la tabla: se limita la espera por el lock.
    _set_lock_timeout()
    op.alter_column(
        'zone_recommendations',
        'reasoning',
        type_=postgresql.JSONB(),
        existing_type=sa.JSON(),
        postgresql_using='reasoning::jsonb',
    )
    op.alter_column(
        'zone_recommendations',
        'metadata',
        type_=postgresql.JSONB(),
        existing_type=sa.JSON(),
        postgresql_using='metadata::jsonb',
    )


def downgrade() -> None:
    _set_lock_timeout()
    op.alter_column(
        'zone_recommendations',
        'reasoning',
        type_=sa.JSON(),
        existing_type=postgresql.JSONB(),
        postgresql_using='reasoning::json',
    )
    op.alter_column(
        'zone_recommendations',
        'metadata',
        type_=sa.JSON(),
        existing_type=postgresql.JSONB(),
        postgresql_using='metadata::json',
    )
