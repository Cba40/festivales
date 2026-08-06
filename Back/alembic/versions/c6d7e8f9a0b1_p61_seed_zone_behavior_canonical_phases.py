"""p61: Seed ZoneBehavior for canonical operational phases.

For every OperationalPhase (Fase 1..10) of the single preserved profile a
ZoneBehavior for each ZoneType must exist. Rows are cloned from the ZoneBehavior
template of the phase with sort_order = 2; the target phase is located
dynamically, never by a fixed UUID. Missing (phase, zone_type) pairs are
inserted; existing pairs are left untouched (idempotent).

Revision ID: c6d7e8f9a0b1
Revises: b5a6c7d8e9f0
Create Date: 2026-08-06

"""
from typing import Sequence, Union

from alembic import op, util
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c6d7e8f9a0b1'
down_revision: Union[str, Sequence[str], None] = 'b5a6c7d8e9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OPERATIONAL_PROFILE_ID = 'a4a316d7-c1ff-4134-9758-a6dab488043c'
SOURCE_SORT_ORDER = 2


def upgrade() -> None:
    # For each canonical phase (1..10) clone every ZoneBehavior of the source
    # phase (sort_order = 2). Pairs (phase, zone_type) that already exist are
    # skipped via ON CONFLICT; id, created_at and updated_at are left to
    # PostgreSQL server defaults. No existing rows are modified.
    op.execute(sa.text(
        """
        INSERT INTO zone_behaviors (
            operational_phase_id,
            zone_type_id,
            saturation_factor,
            availability_factor,
            resource_factor,
            priority_weight,
            density_factor,
            flow_restriction
        )
        SELECT
            tgt.id,
            tpl.zone_type_id,
            tpl.saturation_factor,
            tpl.availability_factor,
            tpl.resource_factor,
            tpl.priority_weight,
            tpl.density_factor,
            tpl.flow_restriction
        FROM operational_phases tgt
        JOIN operational_phases src
          ON src.operational_profile_id = CAST(:profile AS uuid)
         AND src.sort_order = :sort
        JOIN zone_behaviors tpl
          ON tpl.operational_phase_id = src.id
        WHERE tgt.operational_profile_id = CAST(:profile AS uuid)
          AND tgt.sort_order BETWEEN 1 AND 10
        ON CONFLICT ON CONSTRAINT uq_zb_phase_zone_type DO NOTHING
        """
    ).bindparams(
        profile=OPERATIONAL_PROFILE_ID,
        sort=SOURCE_SORT_ORDER,
    ))


def downgrade() -> None:
    raise util.CommandError(
        "Irreversible data migration."
    )