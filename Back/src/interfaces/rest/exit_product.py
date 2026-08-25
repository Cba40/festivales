# backend/src/interfaces/rest/exit_product.py
# S3 (Salir V1): adapter del producto de egreso con scoring determinístico.
#
# Consulta directa a BD + lógica determinística propia del producto:
#   * filtro por modalidad (zones.transporte, canónica Parte 3)
#   * filtro por destino (relación N:N exit_zone_destinations)
#   * distancia Haversine reutilizando la MISMA función del Recommendation
#     Engine (WeightedScoringStrategy._calculate_distance, fuente única)
#   * orden ascendente por distancia cuando hay GPS; si no, alfabético
#   * marca is_nearest en UNA sola zona (la más cercana con coordenadas)
#
# Sin componentes probabilísticos (RFC-EXIT-V1 §16).
# Selección explícita de columnas de zones: nunca carga geometry.

from __future__ import annotations

import math
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
from src.application.recommendation.strategy import WeightedScoringStrategy


async def get_exit_product_adapter(
    db: AsyncSession,
    *,
    event_id: str,
    timestamp: datetime,
    destination_id: str | None = None,
    mode: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> ExitRecommendationResponse:
    # ── 1. Destinos activos del evento ──
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

    # ── 2. Zonas de salida vigentes (+ filtros opcionales modo/destino) ──
    zonas_query = select(
        Zone.id,
        Zone.name,
        Zone.transporte,
        Zone.latitude,
        Zone.longitude,
        Zone.status,
    ).where(
        Zone.event_id == event_id,
        Zone.type == "salida",
        Zone.status != "cerrada",
    )
    if mode is not None:
        # NULL nunca matchea: salidas sin modalidad definida no salen en un modo.
        zonas_query = zonas_query.where(Zone.transporte == mode)
    if destination_id is not None:
        zonas_query = zonas_query.where(
            Zone.id.in_(
                select(exit_zone_destinations_table.c.exit_zone_id).where(
                    exit_zone_destinations_table.c.destination_id == destination_id
                )
            )
        )
    zonas_rows = (await db.execute(zonas_query.order_by(Zone.name))).all()

    zona_ids = [row.id for row in zonas_rows]

    # ── 3. Relaciones N:N para armar la lista de destinos de cada zona ──
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

    # ── 4. Armado de ítems (sin orden final aún) ──
    items: list[tuple[float, str, ExitZoneItem]] = []
    tiene_gps = latitude is not None and longitude is not None
    for row in zonas_rows:
        item = ExitZoneItem(
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
        if tiene_gps and row.latitude is not None and row.longitude is not None:
            distancia = WeightedScoringStrategy._calculate_distance(
                latitude, longitude, row.latitude, row.longitude
            )
        else:
            distancia = math.inf  # sin coordenadas: siempre al final
        items.append((distancia, row.name, item))

    # ── 5. Orden determinístico: distancia asc, desempate por nombre ──
    items.sort(key=lambda t: (t[0], t[1]))

    # ── 6. is_nearest: exactamente la primera con distancia real ──
    marcada = False
    zonas_items: list[ExitZoneItem] = []
    for distancia, _name, item in items:
        if tiene_gps and not marcada and math.isfinite(distancia):
            item.is_nearest = True
            marcada = True
        zonas_items.append(item)

    return ExitRecommendationResponse(
        event_id=event_id,
        timestamp=timestamp.isoformat(),
        zonas=zonas_items,
    )
