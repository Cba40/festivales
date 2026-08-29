"""Resolver puro de recursos territoriales para protocolos (Emergencia V2 - S3).

Dada una ``target_type`` (tipo de emergencia de un protocolo) y una ciudad,
selecciona el recurso ``Emergency`` recomendado de forma determinística:

- Filtra activos por ``city_id`` y ``type``.
- Con ubicación del usuario: ordena por distancia Haversine ASC y luego id ASC.
- Sin ubicación: ordena por nombre ASC y luego id ASC.
- Sin recurso compatible → ``None`` (el endpoint traduce a 404).

Mantiene la separación de dominios: protocolos y recursos permanecen
independientes; esta resolución es un artefacto de composición.
"""
from __future__ import annotations

from src.interfaces.rest.emergency_product import _haversine_distance_km

from app.models.emergency import Emergency, EmergencyType


def resolve_recommended_resource(
    target_type: EmergencyType,
    city_id: str,
    emergencies: list[Emergency],
    latitude: float | None = None,
    longitude: float | None = None,
) -> Emergency | None:
    """Resuelve el recurso territorial recomendado para un target_type.

    - Filtra recursos activos por city_id y type == target_type.
    - Si hay ubicación: ordena por distancia Haversine ASC, id ASC.
    - Si no hay ubicación: ordena por nombre ASC.
    - Retorna el recurso más cercano o None si no hay recurso compatible.
    """
    candidates = [
        e
        for e in emergencies
        if e.city_id == city_id and e.type == target_type and e.active
    ]
    if not candidates:
        return None

    has_user_coords = latitude is not None and longitude is not None

    if has_user_coords:
        def _distance_key(e: Emergency) -> tuple[float, str]:
            if e.latitude is not None and e.longitude is not None:
                d = _haversine_distance_km(
                    latitude, longitude, e.latitude, e.longitude,
                )
            else:
                d = float("inf")  # sin coords van al final
            return (d, e.id)
        return min(candidates, key=_distance_key)

    return min(candidates, key=lambda e: (e.name, e.id))