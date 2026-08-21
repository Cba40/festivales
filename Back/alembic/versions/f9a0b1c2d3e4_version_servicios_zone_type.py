"""Versionar zone_type 'servicios' (aditiva, solo INSERT)

La fila zone_types con slug='servicios' existe en la BD de desarrollo pero fue
insertada manualmente (UUID 0ae81004-90eb-4826-a6f4-0d616e628066), fuera del
versionado de Alembic. Baños V1 depende de ella:

* `_load_zone_type_map` (src/infrastructure/composition/prediction_module.py)
  hace SELECT sin filtro sobre zone_types y clavea por slug, por lo que incluye
  cualquier fila presente en la tabla.
* `_resolve_zone_type_id(type_map, "servicios", "banos")` resuelve en el paso 1
  (`type_map.get("servicios")`) ANTES del fallback SUBTIPO_TO_ZONE_TYPE_SLUG,
  por lo que BathroomModule busca la permanencia en service_configs bajo el
  zone_type_id de esta fila.

En un entorno limpio (migraciones + seeds únicamente) la fila no existe, la
resolución cae al fallback 'bano' y Baños V1 lanza ValueError al no encontrar
la service_config. Esta migración hace reproducible el estado actual.

ADITIVO: no modifica filas existentes ni DDL. Idempotente vía
ON CONFLICT (slug) DO NOTHING:
* En la BD actual es NO-OP (la fila ya existe con este mismo UUID).
* En entorno limpio crea la fila con el MISMO UUID fijo, preservando la
  integridad referencial con las service_configs que lo referencian.

default_factors neutros (1.0): los motores V1 no los consumen; la estructura
JSON replica la de las migraciones a1b2c3d4e5f6 y e8f9a0b1c2d3.

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'f9a0b1c2d3e4'
down_revision: Union[str, Sequence[str], None] = 'e8f9a0b1c2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# UUID YA EXISTENTE en la BD de desarrollo (fila insertada manualmente).
# Se versiona tal cual para mantener la integridad referencial con las
# service_configs que apuntan a este zone_type_id.
_SERVICIOS_ZONE_TYPE_ID = '0ae81004-90eb-4826-a6f4-0d616e628066'


def upgrade() -> None:
    op.execute("""
        INSERT INTO zone_types
            (id, name, slug, icon, description, default_factors, created_at)
        VALUES
        ('{sid}', 'Servicios',   'servicios', 'concierge-bell',
         'Categoría de servicios: baños, hidratación, descanso y salud.',
         $${{
           "pre_apertura": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "temprano": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "pico": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "cierre": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "post_evento": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}}
         }}$$::jsonb, now())
        ON CONFLICT (slug) DO NOTHING
    """.format(sid=_SERVICIOS_ZONE_TYPE_ID))


def downgrade() -> None:
    # Elimina únicamente la fila insertada por esta migración.
    # NOTA: si otras tablas ya referencian este zone_type_id por FK
    # (service_configs, event_day_zone_factors, state_overrides,
    # incident_impacts, zone_behaviors, operational_event_modifiers),
    # el DELETE fallará por restricción de integridad: es intencional,
    # para no borrar datos dependientes en silencio.
    op.execute("DELETE FROM zone_types WHERE slug = 'servicios'")
