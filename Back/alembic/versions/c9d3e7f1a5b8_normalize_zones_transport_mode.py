"""Normalizar zones.transporte a valores canónicos (Salir V1 - S1/PARTE 3)

Canónica RFC-EXIT-V1 para zonas type='salida': peatonal | vehicular | transporte.

* Defensiva: LOWER(TRIM(...)) absorbe variantes de caso/espacios ('AUTO ',
  'Auto', 'Peaton', 'walking').
* Idempotente: re-ejecutar upgrade no cambia nada (los valores ya canónicos
  no vuelven a matchear el WHERE).
* Reversible: downgrade restaura 'vehicular' -> 'auto'. La normalización
  defensiva de peatonal no se revierte (es una corrección de escritura, no
  un cambio de semántica).

ALCANCE ESTRICTO: solo actualiza la columna transporte de filas
type='salida'. Jamás toca coordenadas, nombres, capacities ni zonas de otro
tipo — protege datos editados manualmente en producción (ej.: coordenadas
de 'Salida Norte Auto', drift 2026-07-10).

Las sentencias viven en constantes de módulo para poder verificarlas
funcionalmente sin ejecutar alembic (ver tests/migrations/).

Revision ID: c9d3e7f1a5b8
Revises: f4a6b8c0d2e4
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c9d3e7f1a5b8'
down_revision: Union[str, Sequence[str], None] = 'f4a6b8c0d2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


UPGRADE_STATEMENTS = (
    # Normalizar 'auto' -> 'vehicular' SOLO en zonas type='salida'.
    """
    UPDATE zones
    SET transporte = 'vehicular'
    WHERE type = 'salida' AND LOWER(TRIM(transporte)) = 'auto'
    """,
    # Normalizar variantes de 'peatonal' (defensivo).
    """
    UPDATE zones
    SET transporte = 'peatonal'
    WHERE type = 'salida' AND LOWER(TRIM(transporte)) IN ('peaton', 'peatonal', 'walking')
    """,
)

DOWNGRADE_STATEMENTS = (
    # Revertir 'vehicular' -> 'auto' en zonas de salida.
    """
    UPDATE zones
    SET transporte = 'auto'
    WHERE type = 'salida' AND LOWER(TRIM(transporte)) = 'vehicular'
    """,
)


def upgrade() -> None:
    for statement in UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in DOWNGRADE_STATEMENTS:
        op.execute(statement)
