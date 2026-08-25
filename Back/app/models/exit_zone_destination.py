# backend/app/models/exit_zone_destination.py
# Tabla de asociación N:N entre zones (salidas) y exit_destinations.
# Creada por la migración f4a6b8c0d2e4; espejo del mismo esquema para
# que Base.metadata (tests/create_all y autogenerate) lo refleje.

from sqlalchemy import Column, ForeignKey, Index, String, Table

from app.db.session import Base

exit_zone_destinations_table = Table(
    "exit_zone_destinations",
    Base.metadata,
    Column(
        "exit_zone_id",
        String(36),
        ForeignKey("zones.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "destination_id",
        String(36),
        ForeignKey("exit_destinations.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Index("idx_ezd_zone", "exit_zone_id"),
    Index("idx_ezd_destination", "destination_id"),
)
