# backend/src/interfaces/rest/exit_product.py
# S2 (Salir V1): adapter del producto de egreso.
#
# Consulta directa a BD (sin Recommendation Engine: eso llega en S3).
# Sin scoring, ranking ni is_nearest: se devuelven TODAS las salidas
# vigentes con sus destinos activos; el frontend filtra por modo.
#
# Selección explícita de columnas de zones (id/name/transporte/lat/lng/
# status): nunca carga geometry ni columnas pesadas.

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exit_destination import ExitDestination
from app.models.exit_zone_destination import exit_zone_destinations_table
from app.models.zone import Zone
from app.schemas.exit_product import (
    ExitDestinationItem,
    ExitRecommendationResponse,
    ExitZoneItem,
)


async def get_exit_product_adapter(
    db: AsyncSession,
    *,
    event_id: str,
    timestamp: datetime,
) -> ExitRecommendationResponse:
    # 1. Destinos activos del evento (ordenados alfabéticamente: estable).
    destinos_rows = (
        await db.execute(
            select(ExitDestination.id, ExitDestination.name, ExitDestination.active)
            .where(
                ExitDestination.event_id == event_id,
                ExitDestination.active.is_(True),
            )
            .order_by(ExitDestination.name)
        )
    ).all()
    destinos_por_id = {
        row.id: ExitDestinationItem(id=row.id, name=row.name, active=row.active)
        for row in destinos_rows
    }

    # 2. Zonas de salida vigentes del evento (excluye cerradas).
    zonas_rows = (
        await db.execute(
            select(
                Zone.id,
                Zone.name,
                Zone.transporte,
                Zone.latitude,
                Zone.longitude,
                Zone.status,
            )
            .where(
                Zone.event_id == event_id,
                Zone.type == "salida",
                Zone.status != "cerrada",
            )
            .order_by(Zone.name)
        )
    ).all()

    zona_ids = [row.id for row in zonas_rows]

    # 3. Relaciones N:N de esas zonas con sus destinos.
    relaciones: dict[str, set[str]] = {zona_id: set() for zona_id in zona_ids}
    if zona_ids:
        links_rows = (
            await db.execute(
                select(
                    exit_zone_destinations_table.c.exit_zone_id,
                    exit_zone_destinations_table.c.destination_id,
                ).where(exit_zone_destinations_table.c.exit_zone_id.in_(zona_ids))
            )
        ).all()
        for link in links_rows:
            relaciones[link.exit_zone_id].add(link.destination_id)

    # 4. Armar respuesta.
    zonas_items = [
        ExitZoneItem(
            zone_id=row.id,
            name=row.name,
            transporte=row.transporte,
            lat=row.latitude,
            lng=row.longitude,
            status=row.status,
            destinations=sorted(
                (
                    destinos_por_id[dest_id]
                    for dest_id in relaciones.get(row.id, set())
                    if dest_id in destinos_por_id  # saltea destinos inactivos
                ),
                key=lambda d: d.name,
            ),
        )
        for row in zonas_rows
    ]

    return ExitRecommendationResponse(
        event_id=event_id,
        timestamp=timestamp.isoformat(),
        zonas=zonas_items,
    )
