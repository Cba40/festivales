"""unificar_estados_zone_status_enum_check

Revision ID: b94a2f6cfa5b
Revises: 437c6b0972fc
Create Date: 2026-10-08 18:31:11.682095

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b94a2f6cfa5b'
down_revision: Union[str, Sequence[str], None] = '437c6b0972fc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Valores canónicos (minúsculas, sin espacios) según ZoneStatus
ESTADOS_VALIDOS = ("activa", "restringida", "alerta", "cerrada")
ESTADOS_SET = set(ESTADOS_VALIDOS)


def _normalizar(valor: str | None) -> str | None:
    if valor is None:
        return None
    normalizado = valor.strip().lower()
    mapping = {
        "activa": "activa",
        "active": "activa",
        "restringida": "restringida",
        "restricted": "restringida",
        "con_limites": "restringida",
        "con_límites": "restringida",
        "alerta": "alerta",
        "alert": "alerta",
        "warning": "alerta",
        "cerrada": "cerrada",
        "cerrado": "cerrada",
        "closed": "cerrada",
        "canceled": "cerrada",
        "cancelled": "cerrada",
    }
    return mapping.get(normalizado)


def _column_exists(bind, table: str, column: str) -> bool:
    """Verifica si una columna existe en la tabla."""
    result = bind.execute(sa.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = :table AND column_name = :column
    """), {"table": table, "column": column})
    return result.fetchone() is not None


def upgrade() -> None:
    bind = op.get_bind()

    # Solo aplicar si la tabla zones tiene la columna 'status'
    # (en BD legacy local no existe, en Neon test sí)
    if not _column_exists(bind, "zones", "status"):
        # La tabla no tiene la columna, nada que hacer
        return

    # 1. Normalizar valores existentes en la tabla zones
    result = bind.execute(sa.text("SELECT id, status FROM zones"))
    rows = result.fetchall()

    for row in rows:
        zona_id, status_actual = row.id, row.status
        if status_actual is not None:
            normalizado = _normalizar(status_actual)
            if normalizado is not None and normalizado != status_actual:
                bind.execute(
                    sa.text("UPDATE zones SET status = :val WHERE id = :id"),
                    {"val": normalizado, "id": zona_id},
                )

    # 2. Cambiar el default a 'activa' (ya lo es, pero por claridad)
    op.alter_column("zones", "status",
                    existing_type=sa.String(20),
                    server_default="activa",
                    existing_nullable=False)

    # 3. Agregar CHECK constraint para restringir valores a los 4 canónicos
    op.create_check_constraint(
        constraint_name="ck_zones_status_valido",
        table_name="zones",
        condition=sa.text("status IN ('activa', 'restringida', 'alerta', 'cerrada')"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not _column_exists(bind, "zones", "status"):
        return

    # Eliminar el CHECK constraint
    op.drop_constraint("ck_zones_status_valido", "zones", type_="check")

    # Restaurar default original (ya es 'activa', pero por si acaso)
    op.alter_column("zones", "status",
                    existing_type=sa.String(20),
                    server_default="activa",
                    existing_nullable=False)
