"""Crear tabla zone_subtypes + poblar catálogo canónico

Catálogo de subtipos canónicos con dos familias:

* SERVICIOS (padre: zone_types slug='servicios',
  UUID 0ae81004-90eb-4826-a6f4-0d616e628066, versionado en f9a0b1c2d3e4):
  banos, hidratacion, descanso, salud.
  Estos son los subtipos que el código resuelve vía SUBTIPO_TO_ZONE_TYPE_SLUG
  (prediction_module.py) y que Baños V1 consume (BATHROOM_SUBTIPO='banos').

* COMIDA (padre: zone_types slug='comida', resuelto por subquery):
  foodtruck, comida_al_paso, penas, patio_de_comidas, restaurante.
  Nueva taxonomía gastronómica; reemplaza a largo plazo a rapido/comida/bebida.

ADITIVO: crea una tabla nueva y la puebla con ON CONFLICT DO NOTHING
(idempotente). No modifica tablas ni datos existentes. No toca motores ni
SUBTIPO_TO_ZONE_TYPE_SLUG (fase posterior).

Revision ID: b0c1d2e3f4a5
Revises: f9a0b1c2d3e4
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = 'b0c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = 'f9a0b1c2d3e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ──────────────────────────────────────────────
# UUIDs fijos para seed data (reproducibles).
# Patrón: prefijo 'c' + dígito repetido por subtipo.
# ──────────────────────────────────────────────

_SERVICIOS_ZONE_TYPE_ID = '0ae81004-90eb-4826-a6f4-0d616e628066'

_SUBTYPE_IDS = {
    # SERVICIOS
    'banos':            'c1111111-1111-1111-1111-111111111111',
    'hidratacion':      'c2222222-2222-2222-2222-222222222222',
    'descanso':         'c3333333-3333-3333-3333-333333333333',
    'salud':            'c4444444-4444-4444-4444-444444444444',
    # COMIDA
    'foodtruck':        'c5555555-5555-5555-5555-555555555555',
    'comida_al_paso':   'c6666666-6666-6666-6666-666666666666',
    'penas':            'c7777777-7777-7777-7777-777777777777',
    'patio_de_comidas': 'c8888888-8888-8888-8888-888888888888',
    'restaurante':      'c9999999-9999-9999-9999-999999999999',
}


def upgrade() -> None:
    # ═══════════════════════════════════════════
    # 1. TABLA zone_subtypes
    # ═══════════════════════════════════════════
    op.create_table(
        'zone_subtypes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('zone_type_id', sa.String(36),
                  sa.ForeignKey('zone_types.id'), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('icon', sa.String(100), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('zone_type_id', 'slug', name='uq_zone_subtypes_type_slug'),
    )

    # ═══════════════════════════════════════════
    # 2. SEED — familia SERVICIOS
    # ═══════════════════════════════════════════
    op.execute("""
        INSERT INTO zone_subtypes
            (id, zone_type_id, slug, name, icon, description, sort_order, created_at)
        VALUES
        ('{banos_id}',   '{zt_servicios}', 'banos',       'Baños',       'toilet',      'Sanitarios químicos o baños del predio.', 1, now()),
        ('{hidr_id}',    '{zt_servicios}', 'hidratacion', 'Hidratación', 'droplets',    'Puntos de agua potable e hidratación.',   2, now()),
        ('{desc_id}',    '{zt_servicios}', 'descanso',    'Descanso',    'armchair',    'Áreas de descanso y sombra.',             3, now()),
        ('{salud_id}',   '{zt_servicios}', 'salud',       'Salud',       'heart-pulse', 'Puntos de atención sanitaria.',           4, now())
        ON CONFLICT (zone_type_id, slug) DO NOTHING
    """.format(
        banos_id=_SUBTYPE_IDS['banos'],
        hidr_id=_SUBTYPE_IDS['hidratacion'],
        desc_id=_SUBTYPE_IDS['descanso'],
        salud_id=_SUBTYPE_IDS['salud'],
        zt_servicios=_SERVICIOS_ZONE_TYPE_ID,
    ))

    # ═══════════════════════════════════════════
    # 3. SEED — familia COMIDA (padre por subquery)
    # ═══════════════════════════════════════════
    op.execute("""
        INSERT INTO zone_subtypes
            (id, zone_type_id, slug, name, icon, description, sort_order, created_at)
        SELECT v.id, zt.id, v.slug, v.name, v.icon, v.description, v.sort_order, now()
        FROM (VALUES
            ('{foodtruck_id}',      'foodtruck',        'Foodtruck',        'truck',            'Vehículos de venta de comida rápida.',        1),
            ('{alpaso_id}',         'comida_al_paso',   'Comida al paso',   'sandwich',         'Puestos de comida rápida para llevar.',       2),
            ('{penas_id}',          'penas',            'Peñas',            'guitar',           'Peñas folclóricas con servicio gastronómico.', 3),
            ('{patio_id}',          'patio_de_comidas', 'Patio de comidas', 'utensils-crossed', 'Patios gastronómicos con múltiples puestos.',  4),
            ('{restaurante_id}',    'restaurante',      'Restaurante',      'chef-hat',         'Restaurantes y parrillas con servicio de mesa.', 5)
        ) AS v(id, slug, name, icon, description, sort_order)
        JOIN zone_types zt ON zt.slug = 'comida'
        ON CONFLICT (zone_type_id, slug) DO NOTHING
    """.format(
        foodtruck_id=_SUBTYPE_IDS['foodtruck'],
        alpaso_id=_SUBTYPE_IDS['comida_al_paso'],
        penas_id=_SUBTYPE_IDS['penas'],
        patio_id=_SUBTYPE_IDS['patio_de_comidas'],
        restaurante_id=_SUBTYPE_IDS['restaurante'],
    ))


def downgrade() -> None:
    op.drop_table('zone_subtypes')
