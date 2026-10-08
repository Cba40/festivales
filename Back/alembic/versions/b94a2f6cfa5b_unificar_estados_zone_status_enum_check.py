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

    # ============================================================
    # PASO 1: Normalización agresiva de valores legacy
    # ============================================================
    # Mapear variantes conocidas a sus valores canónicos
    op.execute("""
        UPDATE zones
        SET status = 'activa'
        WHERE LOWER(status) IN (
            'abierto', 'open', 'activo', 'habilitada', 'activa'
        )
    """)

    op.execute("""
        UPDATE zones
        SET status = 'cerrada'
        WHERE LOWER(status) IN (
            'cerrado', 'closed', 'inhabilitada', 'fuera de servicio',
            'bloqueada', 'bloqueado', 'desactivada', 'desactivado'
        )
    """)

    op.execute("""
        UPDATE zones
        SET status = 'restringida'
        WHERE LOWER(status) IN (
            'limitada', 'con limites', 'con límites', 'parcial',
            'restringido', 'restricted', 'limitada'
        )
    """)

    op.execute("""
        UPDATE zones
        SET status = 'alerta'
        WHERE LOWER(status) IN (
            'alerta', 'alert', 'warning', 'advertencia', 'aviso'
        )
    """)

    # Normalizar mayúsculas/minúsculas en valores ya canónicos
    op.execute("""
        UPDATE zones
        SET status = LOWER(status)
        WHERE status IS NOT NULL
    """)

    # ============================================================
    # PASO 2: Fallback de seguridad - convertir CUALQUIER valor
    # no canónico a 'activa' (fallback seguro, evita ocultar zonas)
    # ============================================================
    op.execute("""
        UPDATE zones
        SET status = 'activa'
        WHERE LOWER(status) NOT IN ('activa', 'restringida', 'alerta', 'cerrada')
           OR status IS NULL
    """)

    # ============================================================
    # PASO 3: Cambiar el default a 'activa' (ya lo es, pero por claridad)
    # ============================================================
    op.alter_column("zones", "status",
                    existing_type=sa.String(20),
                    server_default="activa",
                    existing_nullable=False)

    # ============================================================
    # PASO 4: Agregar CHECK constraint (case-insensitive)
    # ============================================================
    op.create_check_constraint(
        constraint_name="ck_zones_status_valido",
        table_name="zones",
        condition=sa.text("LOWER(status) IN ('activa', 'restringida', 'alerta', 'cerrada')"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    # Verificar si la tabla tiene la columna antes de intentar borrar
    result = bind.execute(sa.text("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'zones' AND column_name = 'status'
    """))
    if not result.fetchone():
        return

    # Eliminar el CHECK constraint
    op.drop_constraint("ck_zones_status_valido", "zones", type_="check")

    # Restaurar default original (ya es 'activa', pero por si acaso)
    op.alter_column("zones", "status",
                    existing_type=sa.String(20),
                    server_default="activa",
                    existing_nullable=False)
