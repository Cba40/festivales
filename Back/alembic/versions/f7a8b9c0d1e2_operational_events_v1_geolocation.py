"""operational_events V1.2: geolocation (latitude/longitude)

Revision ID: f7a8b9c0d1e2
Revises: f6g7h8i9j0k1
Create Date: 2026-09-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = 'f6g7h8i9j0k1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Agregar columnas opcionales de geolocalización
    op.add_column('operational_events', sa.Column('latitude', sa.Numeric(10, 8), nullable=True))
    op.add_column('operational_events', sa.Column('longitude', sa.Numeric(11, 8), nullable=True))

    # 2. Agregar constraints CHECK
    op.create_check_constraint(
        'ck_operational_events_latitude',
        'operational_events',
        sa.text('latitude IS NULL OR (latitude BETWEEN -90 AND 90)'),
    )
    op.create_check_constraint(
        'ck_operational_events_longitude',
        'operational_events',
        sa.text('longitude IS NULL OR (longitude BETWEEN -180 AND 180)'),
    )


def downgrade() -> None:
    # 1. Eliminar constraints
    op.drop_constraint('ck_operational_events_longitude', 'operational_events', type_='check')
    op.drop_constraint('ck_operational_events_latitude', 'operational_events', type_='check')

    # 2. Eliminar columnas
    op.drop_column('operational_events', 'longitude')
    op.drop_column('operational_events', 'latitude')