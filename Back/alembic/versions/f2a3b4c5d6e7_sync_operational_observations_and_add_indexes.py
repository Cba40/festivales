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

Prerrequisito anadido en esta iteracion
--------------------------------------
El docstring de arriba dice, con razon, "No hay `create_table`: la tabla ya
existe con datos". Eso es cierto en Neon de produccion y falso en cualquier
base nueva: en este arbol la tabla no la crea ninguna migracion, asi que los
`create_index` de mas abajo fallaban con `relation
"operational_observations" does not exist` y `alembic upgrade head` no podia
correr desde cero. Se agrega un `CREATE TABLE IF NOT EXISTS` con el esquema
declarado en `OperationalObservationModel`, que es exactamente el verificado
contra Neon mas arriba (timestamptz, jsonb, varchar(36)). Es un no-op donde la
tabla ya existe, con lo que no cambia el comportamiento de produccion.

Se agrega tambien `predictions` por el mismo motivo: es otra tabla de `src/`
que ninguna migracion de este arbol crea. No bloquea esta migracion (nada la
tocaba), pero sin ella una base instalada desde cero queda sin la tabla de la
que lee el Context Engine, y el `applying` de este arbol daria exito con una
base incompleta. Esquema tomado de `PredictionModel`, sin FKs por el motivo que
documenta ese propio modelo.

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
import sqlalchemy as sa


revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'a9b8c7d6e5f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 0) Prerrequisitos idempotentes: materializar las dos tablas de `src/` que
    #    ninguna migracion de este arbol creaba. Ver el docstring.
    #
    #    `operational_observations`: esquema de `OperationalObservationModel` en
    #    su estado HISTORICO. Sin FKs, igual que el modelo, y sin los indices que
    #    crea esta misma migracion mas abajo.
    #
    #    `corrected_by` y `corrected_at` NO van aqui a proposito: los agrega
    #    `b4c5d6e7f8a9`, que corre despues. Incluirlos aqui hacia fallar la
    #    cadena con `column "corrected_by" already exists`. Es el mismo criterio
    #    que se aplico en p91 con `snapshot_hash`.
    op.execute(sa.text(
        """
        CREATE TABLE IF NOT EXISTS operational_observations (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            event_day_id varchar(36) NOT NULL,
            zone_id varchar(36) NOT NULL,
            timestamp timestamptz NOT NULL,
            observed_density integer NOT NULL,
            observer_id varchar(36),
            source varchar(50) NOT NULL DEFAULT 'manual',
            "metadata" jsonb,
            created_at timestamptz NOT NULL DEFAULT now()
        )
        """
    ))

    # `predictions`: esquema de `PredictionModel`. El UNIQUE de `timestamp`
    # se crea con su nombre (`uq_predictions_timestamp`) para que coincida con
    # el declarado en el modelo y un `autogenerate` posterior no lo proponga
    # para borrar.
    op.execute(sa.text(
        """
        CREATE TABLE IF NOT EXISTS predictions (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            timestamp timestamp NOT NULL,
            event_day_id varchar(36) NOT NULL,
            knowledge_model_version_id uuid,
            active_phase_id uuid NOT NULL,
            active_event_day_phase_id uuid NOT NULL,
            zone_states_data JSON NOT NULL,
            created_at timestamp NOT NULL DEFAULT now(),
            CONSTRAINT uq_predictions_timestamp UNIQUE (timestamp)
        )
        """
    ))

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
