"""p60: Destructive normalization of operational profiles and phases.

After upgrade exactly one profile exists (ActividadExtendida) with exactly
ten phases (Fase 1..10). Everything else is deleted.

Revision ID: b5a6c7d8e9f0
Revises: 3a2b1c0d9e8f
Create Date: 2026-08-06

"""
from typing import Sequence, Union

from alembic import op, util
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b5a6c7d8e9f0'
down_revision: Union[str, Sequence[str], None] = '3a2b1c0d9e8f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# OperationalProfile to preserve.
ACTIVIDAD_PROFILE_ID = 'a4a316d7-c1ff-4134-9758-a6dab488043c'


def upgrade() -> None:
    # 0) Prerrequisito: el perfil que esta migracion va a preservar tiene que
    #    existir. En la base de desarrollo (creada a mano, no por migraciones)
    #    ya estaba, y por eso el fallo nunca apareció: el paso 3 inserta
    #    `operational_phases` con este UUID como FK, así que sin la fila el
    #    INSERT viola `operational_phases_operational_profile_id_fkey` y
    #    `alembic upgrade head` no puede correr en una base nueva.
    #
    #    El nombre es el que documenta el docstring de esta migracion
    #    ("ActividadExtendida"). `ON CONFLICT DO NOTHING` (sin columna) para que
    #    sea idempotente tanto si ya existe la fila con este id como si el id
    #    chocara por el UNIQUE de `name`: en una base ya sembrada no se toca nada.
    op.execute(sa.text(
        """
        INSERT INTO operational_profiles (id, name, description)
        VALUES (
            CAST(:profile AS uuid),
            'ActividadExtendida',
            'Perfil operativo territorial canonico'
        )
        ON CONFLICT DO NOTHING
        """
    ).bindparams(profile=ACTIVIDAD_PROFILE_ID))

    # 1) Every event_days row points to the preserved profile.
    op.execute(sa.text(
        """
        UPDATE event_days
        SET operational_profile_id = CAST(:profile AS uuid)
        """
    ).bindparams(profile=ACTIVIDAD_PROFILE_ID))

    # 2) Rename the profile's existing phases by sort_order (1 -> "Fase 1", ...).
    op.execute(sa.text(
        """
        UPDATE operational_phases
        SET name = 'Fase ' || sort_order::text
        WHERE operational_profile_id = CAST(:profile AS uuid)
          AND sort_order BETWEEN 1 AND 10
        """
    ).bindparams(profile=ACTIVIDAD_PROFILE_ID))

    # 3) Insert the missing phases to complete Fase 1..10.
    op.execute(sa.text(
        """
        INSERT INTO operational_phases (operational_profile_id, name, sort_order)
        SELECT CAST(:profile AS uuid), 'Fase ' || gs::text, gs
        FROM generate_series(1, 10) AS gs
        WHERE NOT EXISTS (
            SELECT 1
            FROM operational_phases op
            WHERE op.operational_profile_id = CAST(:profile AS uuid)
              AND op.sort_order = gs
        )
        """
    ).bindparams(profile=ACTIVIDAD_PROFILE_ID))

    # 4) Every event_day_phases record points to the definitive phase of the
    #    same sort_order (Fase 1..10 already exist).
    op.execute(sa.text(
        """
        UPDATE event_day_phases edp
        SET operational_phase_id = t.id
        FROM operational_phases src
        JOIN operational_phases t
          ON t.operational_profile_id = CAST(:profile AS uuid)
         AND t.sort_order = src.sort_order
         AND t.sort_order BETWEEN 1 AND 10
        WHERE edp.operational_phase_id = src.id
        """
    ).bindparams(profile=ACTIVIDAD_PROFILE_ID))

    # 5) DELETE every zone_behavior whose phase does not belong to the
    #    preserved profile.
    op.execute(sa.text(
        """
        DELETE FROM zone_behaviors zb
        USING operational_phases p
        WHERE zb.operational_phase_id = p.id
          AND p.operational_profile_id <> CAST(:profile AS uuid)
        """
    ).bindparams(profile=ACTIVIDAD_PROFILE_ID))

    # 6) DELETE every phase that does not belong to the preserved profile.
    op.execute(sa.text(
        """
        DELETE FROM operational_phases
        WHERE operational_profile_id <> CAST(:profile AS uuid)
        """
    ).bindparams(profile=ACTIVIDAD_PROFILE_ID))

    # 7) DELETE every other operational profile.
    op.execute(sa.text(
        """
        DELETE FROM operational_profiles
        WHERE id <> CAST(:profile AS uuid)
        """
    ).bindparams(profile=ACTIVIDAD_PROFILE_ID))


def downgrade() -> None:
    raise util.CommandError(
        "Irreversible data migration."
    )