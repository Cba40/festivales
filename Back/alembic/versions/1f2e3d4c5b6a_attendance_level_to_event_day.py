"""AttendanceLevel ownership moves from Event to EventDay

Revision ID: 1f2e3d4c5b6a
Revises: b3c2d1a0f9e8
Create Date: 2026-08-12

Changes:
  - Adds attendance_levels.event_day_id (FK -> event_days.id).
  - Migrates existing attendance_levels using event_days.attendance_level_id as
    the historical association. If several EventDays reference the same
    AttendanceLevel, an independent copy is created for each EventDay,
    because the new model establishes per-day ownership.
  - Drops attendance_levels.event_id and event_days.attendance_level_id.
  - Replaces event-scoped constraints with event_day-scoped constraints.
  - Makes attendance_levels.event_day_id NOT NULL.
"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1f2e3d4c5b6a'
down_revision: Union[str, Sequence[str], None] = 'b3c2d1a0f9e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _migrate_attendance_levels(conn) -> None:
    """Re-parent attendance_levels to event_days, cloning shared levels."""
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
                "SELECT id, name, min_people, max_people, event_day_id "
                "FROM attendance_levels WHERE id = :al_id"
            ),
            {"al_id": al_id},
        ).fetchone()
        if row is None:
            continue

        original_id, name, min_people, max_people, existing_event_day_id = row

        # First day claims the original row; subsequent days get an
        # independent copy because ownership is per EventDay.
        if claimed.get(original_id) is None:
            claimed[original_id] = day_id
            conn.execute(
                sa.text(
                    "UPDATE attendance_levels SET event_day_id = :eid "
                    "WHERE id = :id"
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

    # Any attendance_level not referenced by an EventDay has no EventDay scope
    # in the new model. It cannot satisfy NOT NULL and has no valid owner, so it
    # is removed. (Residual risk: see final report.)
    conn.execute(
        sa.text(
            "DELETE FROM attendance_levels WHERE event_day_id IS NULL"
        )
    )


def upgrade() -> None:
    # 1. Add temporary nullable column.
    op.add_column(
        "attendance_levels",
        sa.Column("event_day_id", sa.String(36), nullable=True),
    )

    # 2. Migrate existing data (historical association via event_days.attendance_level_id).
    conn = op.get_bind()
    _migrate_attendance_levels(conn)

    # 3. Drop old event-scoped constraints.
    op.drop_constraint(
        "uq_attendance_level_event_name", "attendance_levels", type_="unique"
    )
    op.drop_constraint(
        "uq_attendance_level_range", "attendance_levels", type_="unique"
    )

    # 4. Drop legacy columns (their FKs are dropped with them).
    op.drop_column("attendance_levels", "event_id")
    op.drop_column("event_days", "attendance_level_id")

    # 5. Create new event_day-scoped constraints.
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

    # 6. Make event_day_id NOT NULL.
    op.alter_column("attendance_levels", "event_day_id", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_attendance_levels_event_day_id", table_name="attendance_levels")
    op.drop_constraint(
        "uq_attendance_level_range", "attendance_levels", type_="unique"
    )
    op.drop_constraint(
        "uq_attendance_level_event_day_name", "attendance_levels", type_="unique"
    )

    op.add_column(
        "attendance_levels",
        sa.Column("event_id", sa.String(36), sa.ForeignKey("events.id"), nullable=True),
    )

    # Re-associate a single attendance_level per event day (best effort).
    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            "SELECT al.id, ed.event_id FROM attendance_levels al "
            "JOIN event_days ed ON ed.id = al.event_day_id"
        )
    ).fetchall()
    for al_id, event_id in rows:
        claimed = conn.execute(
            sa.text(
                "SELECT id FROM attendance_levels "
                "WHERE event_id = :eid ORDER BY min_people LIMIT 1"
            ),
            {"eid": event_id},
        ).fetchone()
        if claimed is None:
            conn.execute(
                sa.text(
                    "UPDATE attendance_levels SET event_id = :eid WHERE id = :id"
                ),
                {"eid": event_id, "id": al_id},
            )

    op.alter_column("attendance_levels", "event_id", nullable=False)

    op.create_unique_constraint(
        "uq_attendance_level_event_name",
        "attendance_levels",
        ["event_id", "name"],
    )
    op.create_unique_constraint(
        "uq_attendance_level_range",
        "attendance_levels",
        ["event_id", "min_people", "max_people"],
    )

    op.add_column(
        "event_days",
        sa.Column(
            "attendance_level_id",
            sa.String(36),
            sa.ForeignKey("attendance_levels.id"),
            nullable=False,
        ),
    )
    conn = op.get_bind()
    links = conn.execute(
        sa.text(
            "SELECT ed.id, al.id FROM event_days ed "
            "JOIN attendance_levels al ON ed.id = al.event_day_id"
        )
    ).fetchall()
    for day_id, al_id in links:
        conn.execute(
            sa.text(
                "UPDATE event_days SET attendance_level_id = :al_id WHERE id = :id"
            ),
            {"al_id": al_id, "id": day_id},
        )

    op.drop_column("attendance_levels", "event_day_id")