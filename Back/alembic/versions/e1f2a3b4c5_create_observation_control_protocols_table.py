"""Crear tabla observation_control_protocols

Reglas de control de observaciones por evento: si una métrica que el motor ya
publica por zona supera un umbral, debería haberse registrado una observación
cada N minutos.

La tabla es ADITIVA: no modifica ninguna existente. Crea dos enums propios
(``observation_trigger_metric`` y ``observation_trigger_operator``) y tres FKs
hacia tablas que ya existen (``events``, ``event_days``, ``zone_types``), por lo
que esas FKs van con ``create_type=False``: no deben intentar crear again un
tipo ajeno.

``zone_type_id`` usa ``ON DELETE SET NULL`` a propósito: borrar un tipo de zona
desactiva el filtro de la regla, no borra la regla.

Sujeto a: UNIQUE(event_id, name),
CHECK(action_interval_minutes BETWEEN 1 AND 1440), CHECK("order" >= 0).
En ``order`` (palabra reservada) el identificador va entre comillas, igual que en
``emergency_protocols``.

Revision ID: e1f2a3b4c5
Revises: b4c5d6e7f8a9
Create Date: 2026-10-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5"
down_revision: Union[str, Sequence[str], None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "observation_control_protocols",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(36), nullable=False),
        sa.Column("event_day_id", sa.String(36), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column(
            "trigger_metric",
            sa.Enum(
                "saturation_level",
                "availability",
                "estimated_wait",
                "confidence",
                "projected_density",
                name="observation_trigger_metric",
            ),
            nullable=False,
        ),
        sa.Column(
            "trigger_operator",
            sa.Enum("gt", "gte", "lt", "lte", name="observation_trigger_operator"),
            nullable=False,
            server_default="gt",
        ),
        sa.Column("threshold_value", sa.Numeric(6, 2), nullable=False),
        sa.Column("action_interval_minutes", sa.Integer(), nullable=False),
        sa.Column("zone_type_id", sa.String(36), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"], ["events.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["event_day_id"], ["event_days.id"], ondelete="CASCADE"
        ),
        # SET NULL, no CASCADE: borrar un tipo de zona desactiva el filtro de la
        # regla en vez de borrar la regla.
        sa.ForeignKeyConstraint(
            ["zone_type_id"], ["zone_types.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "event_id", "name", name="uq_observation_control_protocols_event_name"
        ),
        sa.CheckConstraint(
            "action_interval_minutes BETWEEN 1 AND 1440",
            name="ck_observation_control_protocols_interval",
        ),
        sa.CheckConstraint('"order" >= 0', name="ck_observation_control_protocols_order"),
    )


def downgrade() -> None:
    op.drop_table("observation_control_protocols")
    op.execute("DROP TYPE IF EXISTS observation_trigger_metric")
    op.execute("DROP TYPE IF EXISTS observation_trigger_operator")