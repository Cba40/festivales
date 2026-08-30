"""Agregar subtipo 'cajeros' al catálogo de zone_subtypes (aditiva, solo INSERT)

El subtipo canónico 'salud' modela puestos sanitarios con métricas de
saturación, tiempo de espera y confianza (motor de recomendación AHEC/Security).
'Cajeros' es un servicio básico que NO debe heredar esas métricas ni el motor
de predicción de salud.

Esta migración agrega un subtipo 'cajeros' independiente bajo el zone_type
'servicios' (UUID 0ae81004-90eb-4826-a6f4-0d616e628066), versionado en
f9a0b1c2d3e4. Es puramente de catálogo: no toca 'salud' ni sus datos.

ADITIVO: idempotente vía ON CONFLICT (zone_type_id, slug) DO NOTHING.
No modifica filas existentes ni DDL.

Revision ID: d1e2f3a4b5c6
Revises: c8d9e0f1a2b3
Create Date: 2026-08-29 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c8d9e0f1a2b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SERVICIOS_ZONE_TYPE_ID = '0ae81004-90eb-4826-a6f4-0d616e628066'

# UUID fijo reproducible: patrón prefijo 'c' + dígito/nueva secuencia.
_CAJEROS_SUBTYPE_ID = 'caaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'


def upgrade() -> None:
    op.execute("""
        INSERT INTO zone_subtypes
            (id, zone_type_id, slug, name, icon, description, sort_order, created_at)
        VALUES
        ('{caj_id}', '{zt_servicios}', 'cajeros', 'Cajeros', 'credit-card',
         'Cajeros automáticos disponibles.', 5, now())
        ON CONFLICT (zone_type_id, slug) DO NOTHING
    """.format(
        caj_id=_CAJEROS_SUBTYPE_ID,
        zt_servicios=_SERVICIOS_ZONE_TYPE_ID,
    ))


def downgrade() -> None:
    # Elimina únicamente la fila insertada por esta migración.
    op.execute("""
        DELETE FROM zone_subtypes
        WHERE zone_type_id = '{zt_servicios}' AND slug = 'cajeros'
    """.format(zt_servicios=_SERVICIOS_ZONE_TYPE_ID))
