"""Restore Event-scoped AttendanceLevel and EventDay.attendance_level_id.

Revision ID: c7d8e9f0a1b2
Revises: 1f2e3d4c5b6a
Create Date: 2026-08-13

Modelo definitivo:
  Event
   └── AttendanceLevels[]        ← catálogo del evento
  EventDay
   └── attendance_level_id       ← selecciona UN nivel (puede compartirse)

Se revierte la semántica por EventDay introducida en 1f2e3d4c5b6a:
  - attendance_levels vuelve a depender de events (event_id).
  - event_days vuelve a seleccionar un attendance_level (attendance_level_id).
  - se elimina attendance_levels.event_day_id.
  - se eliminan las constraints event_day-scoped.
  - NO se restauran constraints de unicidad de rangos/nombres: el catálogo
    admite niveles con rangos iguales o solapados. Solo se conservan las
    constraints de coherencia técnica del rango (min>=0, max>min).

La relación actual (cada attendance_level pertenece a un event_day) se
preserva cuando existen registros: event_id se reconstruye desde el event_day
propietario y event_days.attendance_level_id desde el nivel propietario.

event_days.attendance_level_id queda NULLABLE: las jornadas existentes sin
nivel (por ejemplo, attendance_levels vacío) se conservan con NULL y podrán
asignarse a un nivel posteriormente. NO se fuerza NOT NULL y NO se crean
niveles automáticamente.
"""

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = "1f2e3d4c5b6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Restore event ownership on attendance_levels ──────────────
    op.add_column(
        "attendance_levels",
        sa.Column("event_id", sa.String(36), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE attendance_levels al
            SET event_id = ed.event_id
            FROM event_days ed
            WHERE ed.id = al.event_day_id
            """
        )
    )

    # Defensa: niveles sin event_day propietario no pueden preservarse (no
    # tienen evento ni jornada). Tras 1f2e3d4c5b6a todos tienen event_day_id.
    op.execute(
        sa.text(
            """
            DELETE FROM attendance_levels WHERE event_id IS NULL
            """
        )
    )

    op.alter_column("attendance_levels", "event_id", nullable=False)

    # ── 2. Restore EventDay -> AttendanceLevel selection ─────────────
    op.add_column(
        "event_days",
        sa.Column("attendance_level_id", sa.String(36), nullable=True),
    )

    # Cada EventDay hereda su nivel del ownership por jornada vigente.
    # Se elige determinísticamente (min_people, id) por si existiera más de
    # un nivel con el mismo event_day_id.
    op.execute(
        sa.text(
            """
            UPDATE event_days ed
            SET attendance_level_id = (
                SELECT al.id
                FROM attendance_levels al
                WHERE al.event_day_id = ed.id
                ORDER BY al.min_people ASC, al.id ASC
                LIMIT 1
            )
            """
        )
    )

    op.create_foreign_key(
        "fk_event_days_attendance_level_id",
        "event_days",
        "attendance_levels",
        ["attendance_level_id"],
        ["id"],
    )

    # attendance_level_id queda NULLABLE de forma definitiva: las jornadas
    # existentes sin nivel se conservan válidamente con NULL (no se inventan
    # ni se asignan niveles). NO se ejecuta ALTER ... SET NOT NULL.
    # La FK hacia attendance_levels.id se mantiene: solo acepta NULL o un
    # nivel existente.

    # ── 3. Remove event_day-scoped ownership and its constraints ─────
    op.drop_index("ix_attendance_levels_event_day_id", table_name="attendance_levels")
    op.drop_constraint("uq_attendance_level_range", "attendance_levels", type_="unique")
    op.drop_constraint("uq_attendance_level_event_day_name", "attendance_levels", type_="unique")
    op.drop_column("attendance_levels", "event_day_id")

    op.create_foreign_key(
        "fk_attendance_levels_event_id",
        "attendance_levels",
        "events",
        ["event_id"],
        ["id"],
    )

    # ── 4. Coherence-only constraints (no range/name uniqueness) ─────
    op.create_check_constraint(
        "chk_attendance_level_min_nonneg",
        "attendance_levels",
        "min_people >= 0",
    )
    op.create_check_constraint(
        "chk_attendance_level_max_gt_min",
        "attendance_levels",
        "max_people IS NULL OR max_people > min_people",
    )


def downgrade() -> None:
    conn = op.get_bind()

    op.drop_constraint("chk_attendance_level_max_gt_min", "attendance_levels", type_="check")
    op.drop_constraint("chk_attendance_level_min_nonneg", "attendance_levels", type_="check")
    op.drop_constraint("fk_attendance_levels_event_id", "attendance_levels", type_="foreignkey")

    # Re-parent to event_days, cloning shared levels (per-day ownership).
    op.add_column(
        "attendance_levels",
        sa.Column("event_day_id", sa.String(36), nullable=True),
    )

    day_rows = conn.execute(
        sa.text(
            "SELECT id, attendance_level_id FROM event_days "
            "WHERE attendance_level_id IS NOT NULL"
        )
    ).fetchall()

    claimed: dict[str, str] = {}
    for day_id, al_id in day_rows:
        row = conn.execute(
            sa.text(
                "SELECT id, name, min_people, max_people "
                "FROM attendance_levels WHERE id = :al_id"
            ),
            {"al_id": al_id},
        ).fetchone()
        if row is None:
            continue
        original_id, name, min_people, max_people = row

        if claimed.get(original_id) is None:
            claimed[original_id] = day_id
            conn.execute(
                sa.text(
                    "UPDATE attendance_levels SET event_day_id = :eid WHERE id = :id"
                ),
                {"eid": day_id, "id": original_id},
            )
        else:
            new_id = str(uuid.uuid4())
            conn.execute(
                sa.text(
                    "INSERT INTO attendance_levels "
                    "(id, event_day_id, name, min_people, max_people) "
                    "VALUES (:id, :eid, :name, :min_people, :max_people)"
                ),
                {
                    "id": new_id,
                    "eid": day_id,
                    "name": name,
                    "min_people": min_people,
                    "max_people": max_people,
                },
            )

    conn.execute(
        sa.text(
            "DELETE FROM attendance_levels WHERE event_day_id IS NULL"
        )
    )

    op.alter_column("attendance_levels", "event_day_id", nullable=False)

    op.drop_constraint("fk_event_days_attendance_level_id", "event_days", type_="foreignkey")
    op.drop_column("event_days", "attendance_level_id")

    op.create_unique_constraint(
        "uq_attendance_level_event_day_name",
        "attendance_levels",
        ["event_day_id", "name"],
    )
    op.create_unique_constraint(
        "uq_attendance_level_range",
        "attendance_levels",
        ["event_day_id", "min_people", "max_people"],
    )
    op.create_index(
        "ix_attendance_levels_event_day_id",
        "attendance_levels",
        ["event_day_id"],
    )

    op.drop_column("attendance_levels", "event_id")
