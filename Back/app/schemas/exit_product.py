# backend/app/schemas/exit_product.py
# S2 (Salir V1): DTOs del producto de egreso.
# V1 sin scoring ni ranking: solo salidas vigentes con sus destinos activos.

from pydantic import BaseModel

# Canónica RFC-EXIT-V1 / Parte 3 para zonas type='salida':
# peatonal | vehicular | transporte.
#
# `zones.transporte` es nullable en la base, así que el valor puede faltar. El
# adapter lo sustituye por este texto antes de armar el DTO, pero el campo queda
# declarado opcional para que una fila rara nunca pueda tumbar el endpoint entero
# con un 500: antes, un único `salida` sin modalidad, alcanzable por API, seed o
# edición manual de BD, reventaba la respuesta completa para todos los usuarios.
TRANSPORTE_NO_ESPECIFICADO = "No especificado"


class ExitDestinationItem(BaseModel):
    id: str
    name: str
    active: bool


class ExitZoneItem(BaseModel):
    zone_id: str
    name: str
    # Nullable a propósito: es la segunda barrera contra el 500. La primera es
    # que el adapter nunca deje pasar un None (usa TRANSPORTE_NO_ESPECIFICADO).
    # Verificarla en el schema evita depender de que todo camino de entrada
    # pase por el adapter.
    transporte: str | None = None  # peatonal | vehicular | transporte (canónica Parte 3)
    lat: float | None = None
    lng: float | None = None
    status: str
    is_nearest: bool = False
    destinations: list[ExitDestinationItem]


class ExitRecommendationResponse(BaseModel):
    event_id: str
    timestamp: str
    zonas: list[ExitZoneItem]
