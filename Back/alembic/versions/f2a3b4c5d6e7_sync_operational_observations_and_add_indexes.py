"""sync operational_observations with production and add its missing indexes

Revision ID: f2a3b4c5d6e7
Revises: a9b8c7d6e5f4
Create Date: 2026-09-28

Por que esta migracion existe y por que NO lleva un create_table
----------------------------------------------------------------
`operational_observations` ya existe en Neon con 17 filas. Nunca fue creada
por una migracion de este arbol: la unica revision que la materializa,
`d9e0f1a2b3c4`, vive en el arbol huerfano
(`src/infrastructure/persistence/migrations/versions/`), al que `alembic.ini`
no apunta. Para este arbol la tabla venia siendo invisible.

Verificado contra Neon (read-only):

    timestamp    timestamp with time zone
    metadata     jsonb
    observer_id  character varying(36)
    filas        17

Ademas, `OperationalObservationModel` vivia en
`src.infrastructure.db.base.Base`, un registro distinto del que `env.py`
declara como target_metadata. Consecuencia medida: antes de corregir
`env.py`, `alembic revision --autogenerate` generaba
`op.drop_table('operational_observations')` (ademas de `predictions` y
`knowledge_model_versions`). Es decir, el proximo autogenerate aplicado en
produccion habria borrado las 17 filas.

Esta migracion es deliberadamente ADITIVA y NO toca ninguna columna:

* No hay `create_table`: la tabla ya existe con datos.
* No hay `alter_column`: los tipos del modelo ya coinciden con los de Neon
  (`DateTime(timezone=True)`, `JSONB`, `String(36)`). El modelo se ajusto al
  esquema, no al reves.
* No hay `drop_table`, `drop_column` ni `rename`: no hay nada que descartar.

Lo unico que agrega son los indices que el CRUD necesita y que no existian.
Se crean con `IF NOT EXISTS` para que la migracion sea idempotente y no
falle si el indice ya estuviera presente.

Sobre los indices
-----------------
`app/crud/operational_observation.py::_find_observation_window` filtra por
`zone_id` y acota `timestamp` con `>= since` / `<= until`, ordenando por
`timestamp DESC`. Esa consulta se ejecuta en cada POST (ventana anti-spam de
15 minutos, lineas 194-198), o sea en la ruta de escritura.

Un indice compuesto `(zone_id, timestamp)` cubre ese caso y además el
`zone_id` como prefijo, asi que hace redundante un indice separado solo por
`zone_id`. Por eso se agrega el compuesto y no dos indices unitarios.

El indice unitario sobre `timestamp` si se mantiene: lo necesita el
`ORDER BY timestamp` de `find_all` (linea 261) cuando el filtro es solo por
`event_day_id`.

Con 17 filas el beneficio hoy es nulo. Se agrega para que el indice exista
antes de que la tabla crezca, y para que no dependa de que alguien recuerde
crearlo a mano.

Revision ID: f2a3b4c5d6e7
Revises: a9b8c7d6e5f4
Create Date: 2026-09-28

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'a9b8c7d6e5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_operational_observations_zone_id_timestamp',
        'operational_observations',
        ['zone_id', 'timestamp'],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        'ix_operational_observations_timestamp',
        'operational_observations',
        ['timestamp'],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index(
        'ix_operational_observations_timestamp',
        table_name='operational_observations',
        if_exists=True,
    )
    op.drop_index(
        'ix_operational_observations_zone_id_timestamp',
        table_name='operational_observations',
        if_exists=True,
    )
