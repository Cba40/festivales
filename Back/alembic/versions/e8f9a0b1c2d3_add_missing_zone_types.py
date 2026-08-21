"""Add missing zone_types (aditiva, solo INSERT)

El catálogo de zone_types de la migración P2 (a1b2c3d4e5f6) tiene 6 slugs,
pero el código y los datos operativos reales referencian 7 slugs que no
existían. Sin ellos, PredictionModule.execute() lanza ValueError al resolver
el zone_type_id de esas zonas (src/infrastructure/composition/prediction_module.py,
_resolve_zone_type_id / SUBTIPO_TO_ZONE_TYPE_SLUG).

Slugs insertados (coinciden EXACTOS con las referencias del código):
    estacionamiento  -> parking_module.PARKING_ZONE_TYPE, strategy.PARKING_TYPE,
                        RequestedAction.SEEK_PARKING, zones.type en seed.py
    comida           -> RequestedAction.SEEK_FOOD, zones.type en seed.py
    transporte       -> RequestedAction.SEEK_TRANSPORT, zones.type en seed.py
    hospedaje        -> RequestedAction.SEEK_ACCOMMODATION, zones.type en seed.py
    salida           -> RequestedAction.SEEK_EXIT, zones.type en seed.py
    descanso         -> SUBTIPO_TO_ZONE_TYPE_SLUG["descanso"], SEEK_REST,
                        zones.subtipo en seed.py
    salud            -> SUBTIPO_TO_ZONE_TYPE_SLUG["salud"], SEEK_HEALTH,
                        zones.subtipo en seed.py

ADITIVO: no modifica filas existentes ni DDL. Idempotente vía
ON CONFLICT (slug) DO NOTHING. default_factors neutros (1.0): los motores V1
no los consumen; la estructura JSON replica la de P2 (clave por event_state).

Revision ID: e8f9a0b1c2d3
Revises: d4e5f6a7b8c9
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = 'e8f9a0b1c2d3'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ──────────────────────────────────────────────
# UUIDs fijos para seed data (reproducibles).
# Patrón P2 (_ZONE_TYPE_IDS): prefijo 'b' + dígito repetido.
# P2 usó b1..b6; aquí continúan b7..bd sin colisionar.
# ──────────────────────────────────────────────

_MISSING_ZONE_TYPE_IDS = {
    'estacionamiento': 'b7777777-7777-7777-7777-777777777777',
    'comida':          'b8888888-8888-8888-8888-888888888888',
    'transporte':      'b9999999-9999-9999-9999-999999999999',
    'hospedaje':       'baaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    'salida':          'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    'descanso':        'bccccccc-cccc-cccc-cccc-cccccccccccc',
    'salud':           'bddddddd-dddd-dddd-dddd-dddddddddddd',
}

_MISSING_ZONE_TYPE_SLUGS = (
    'estacionamiento', 'comida', 'transporte', 'hospedaje',
    'salida', 'descanso', 'salud',
)


def upgrade() -> None:
    op.execute("""
        INSERT INTO zone_types
            (id, name, slug, icon, description, default_factors, created_at)
        VALUES
        ('{est_id}', 'Estacionamiento',   'estacionamiento', 'car',
         'Estacionamientos y zonas de vehículos.',
         $${{
           "pre_apertura": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "temprano": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "pico": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "cierre": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "post_evento": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}}
         }}$$::jsonb, now()),

        ('{com_id}', 'Comida',   'comida', 'utensils',
         'Zonas de venta de comida.',
         $${{
           "pre_apertura": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "temprano": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "pico": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "cierre": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "post_evento": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}}
         }}$$::jsonb, now()),

        ('{tra_id}', 'Transporte',   'transporte', 'bus',
         'Paradas y puntos de transporte.',
         $${{
           "pre_apertura": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "temprano": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "pico": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "cierre": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "post_evento": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}}
         }}$$::jsonb, now()),

        ('{hos_id}', 'Hospedaje',   'hospedaje', 'bed',
         'Alojamientos: hoteles, hostels y campings.',
         $${{
           "pre_apertura": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "temprano": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "pico": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "cierre": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "post_evento": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}}
         }}$$::jsonb, now()),

        ('{sal_id}', 'Salida',   'salida', 'door-open',
         'Zonas de salida del predio.',
         $${{
           "pre_apertura": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "temprano": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "pico": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "cierre": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "post_evento": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}}
         }}$$::jsonb, now()),

        ('{des_id}', 'Descanso',   'descanso', 'armchair',
         'Áreas de descanso y sombra.',
         $${{
           "pre_apertura": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "temprano": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "pico": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "cierre": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "post_evento": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}}
         }}$$::jsonb, now()),

        ('{sau_id}', 'Salud',   'salud', 'heart-pulse',
         'Puntos de atención sanitaria.',
         $${{
           "pre_apertura": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "temprano": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "pico": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "cierre": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}},
           "post_evento": {{"saturation": 1.0, "attendance": 1.0, "resource": 1.0}}
         }}$$::jsonb, now())
        ON CONFLICT (slug) DO NOTHING
    """.format(
        est_id=_MISSING_ZONE_TYPE_IDS['estacionamiento'],
        com_id=_MISSING_ZONE_TYPE_IDS['comida'],
        tra_id=_MISSING_ZONE_TYPE_IDS['transporte'],
        hos_id=_MISSING_ZONE_TYPE_IDS['hospedaje'],
        sal_id=_MISSING_ZONE_TYPE_IDS['salida'],
        des_id=_MISSING_ZONE_TYPE_IDS['descanso'],
        sau_id=_MISSING_ZONE_TYPE_IDS['salud'],
    ))


def downgrade() -> None:
    # Elimina únicamente las 7 filas insertadas por esta migración.
    # NOTA: si otras tablas ya referencian estos ids por FK
    # (event_day_zone_factors, state_overrides, incident_impacts,
    # service_configs, zone_behaviors, operational_event_modifiers),
    # el DELETE fallará por restricción de integridad: es intencional,
    # para no borrar datos dependientes en silencio.
    slugs = ", ".join(f"'{s}'" for s in _MISSING_ZONE_TYPE_SLUGS)
    op.execute(f"DELETE FROM zone_types WHERE slug IN ({slugs})")
