"""REST adapter: recomendaciones determinísticas de emergencia.

Producto dedicado del módulo Emergencia V1. Reemplaza el motor probabilístico
genérico (``/recommendations``) por un query directo y determinístico a la tabla
``emergencies`` (mismo patrón de composición que Hospedaje y Transporte V2).

Las emergencias sin coordenadas (tipicamente ``numero_emergencia`` como 911, 107
o 100) se listan al final cuando el usuario provee GPS, con ``distance_km = None``.
"""
from __future__ import annotations

import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emergency import Emergency, EmergencyType
from app.schemas.emergency import (
    EmergencyItem,
    EmergencyRecommendationResponse,
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


def _sort_key_name(item: EmergencyItem) -> str:
    return (item.name or "").lower()


def _sort_key_distance(item: EmergencyItem) -> float:
    # Sin distancia válida (sin coords de la emergencia) van al final.
    if item.distance_km is None:
        return float("inf")
    return item.distance_km


async def get_emergency_product_adapter(
    db: AsyncSession,
    *,
    city_id: str,
    emergency_type: EmergencyType | None = None,
    user_latitude: float | None = None,
    user_longitude: float | None = None,
    limit: int = 20,
) -> EmergencyRecommendationResponse:
    """Recomendaciones determinísticas de emergencias para una ciudad.

    Lógica:
    1. Filtra ``emergencies`` por ``city_id`` y ``active=True``.
    2. Si se provee ``emergency_type``, filtra por ese tipo.
    3. Calcula distancia Haversine en km si el usuario provee coordenadas
       (solo para emergencias con lat/long).
    4. Ordena: con GPS, primero las que tienen distancia (ascendente) y luego
       las que no tienen coordenadas (``distance_km = None``); sin GPS, ordena
       alfabéticamente por nombre.
    5. Trunca a ``limit``.
    """
    stmt = (
        select(Emergency)
        .where(Emergency.city_id == city_id)
        .where(Emergency.active == True)  # noqa: E712
    )
    if emergency_type is not None:
        stmt = stmt.where(Emergency.type == emergency_type)

    rows = (await db.execute(stmt)).scalars().all()

    has_user_coords = (
        user_latitude is not None and user_longitude is not None
    )

    items: list[EmergencyItem] = []
    for e in rows:
        distance_km: float | None = None
        if (
            has_user_coords
            and e.latitude is not None
            and e.longitude is not None
            and user_latitude is not None
            and user_longitude is not None
        ):
            distance_km = round(
                _haversine_distance_km(
                    user_latitude, user_longitude, e.latitude, e.longitude,
                ),
                3,
            )
        items.append(
            EmergencyItem(
                id=e.id,
                name=e.name,
                type=e.type,
                phone=e.phone,
                emergency_number=e.emergency_number,
                address=e.address,
                reference=e.reference,
                latitude=e.latitude,
                longitude=e.longitude,
                services=e.services,
                schedule=e.schedule,
                active=e.active,
                distance_km=distance_km,
            )
        )

    if has_user_coords:
        items.sort(key=_sort_key_distance)
    else:
        items.sort(key=_sort_key_name)

    return EmergencyRecommendationResponse(emergencies=items[:limit])
