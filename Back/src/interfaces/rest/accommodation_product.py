"""REST adapter: recomendaciones determinísticas de hospedaje.

Producto dedicado del módulo Hospedaje V1. Reemplaza el motor probabilístico
genérico (``/recommendations``) por un query directo y determinístico a la tabla
``accommodations`` (mismo patrón de composición que Transporte V2).
"""
from __future__ import annotations

import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accommodation import Accommodation, AccommodationType
from app.schemas.accommodation import (
    AccommodationItem,
    AccommodationRecommendationResponse,
)


def _haversine_distance_km(
    lat1: float, lon1: float, lat2: float, lon2: float,
) -> float:
    """Distancia ortodrómica (Haversine) entre dos coordenadas, en km."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    # Radio medio de la Tierra en km
    return 6_371.0 * c


def _sort_key_name(item: AccommodationItem) -> str:
    return (item.name or "").lower()


def _sort_key_distance(item: AccommodationItem) -> float:
    # Sin distancia válida (No GPS) las opciones sin coords van al final.
    if item.distance_km is None:
        return float("inf")
    return item.distance_km


async def get_accommodation_product_adapter(
    db: AsyncSession,
    *,
    event_id: str,
    acc_type: AccommodationType | None = None,
    user_latitude: float | None = None,
    user_longitude: float | None = None,
    limit: int = 20,
) -> AccommodationRecommendationResponse:
    """Recomendaciones determinísticas de alojamiento.

    Lógica:
    1. Filtra ``accommodations`` por ``event_id`` y ``active=True``.
    2. Si se provee ``acc_type``, filtra por ese tipo.
    3. Calcula distancia Haversine en km si el usuario provee coordenadas.
    4. Ordena por distancia (con GPS) o por nombre (sin GPS).
    5. Trunca a ``limit``.
    """
    stmt = (
        select(Accommodation)
        .where(Accommodation.event_id == event_id)
        .where(Accommodation.active == True)  # noqa: E712
    )
    if acc_type is not None:
        stmt = stmt.where(Accommodation.type == acc_type)

    rows = (await db.execute(stmt)).scalars().all()

    has_user_coords = (
        user_latitude is not None and user_longitude is not None
    )

    items: list[AccommodationItem] = []
    for a in rows:
        distance_km: float | None = None
        if (
            has_user_coords
            and a.latitude is not None
            and a.longitude is not None
            and user_latitude is not None
            and user_longitude is not None
        ):
            distance_km = round(
                _haversine_distance_km(
                    user_latitude, user_longitude, a.latitude, a.longitude,
                ),
                3,
            )
        items.append(
            AccommodationItem(
                id=a.id,
                event_id=a.event_id,
                name=a.name,
                type=a.type,
                address=a.address,
                reference=a.reference,
                latitude=a.latitude,
                longitude=a.longitude,
                phone=a.phone,
                website=a.website,
                official_info_url=a.official_info_url,
                active=a.active,
                distance_km=distance_km,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
        )

    if has_user_coords:
        items.sort(key=_sort_key_distance)
    else:
        items.sort(key=_sort_key_name)

    return AccommodationRecommendationResponse(
        event_id=event_id,
        accommodations=items[:limit],
    )
