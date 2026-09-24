"""Telemetría de interacciones con servicios municipales (Analytics V1).

Registra UNA fila en ``service_interaction_log`` por request efectivo a un
endpoint de producto. Usa una sesión AsyncSession propia e independiente de la
transacción del handler: el commit/rollback del log NUNCA toca la transacción
del producto. Telemetría secundaria: una falla al persistir no se propaga y no
altera ni la respuesta ni el comportamiento HTTP del endpoint.
"""
import logging
from datetime import datetime

from app.db.session import AsyncSessionLocal
from app.models.service_interaction_log import (
    INTERACTION_TYPES,
    REQUEST_ORIGINS,
    ServiceInteractionLog,
)

logger = logging.getLogger(__name__)

REQUEST_ORIGIN_HEADER = "X-Request-Origin"

ALLOWED_CLIENT_ORIGINS = frozenset({"prefetch", "user"})


def resolve_request_origin(x_request_origin: str | None) -> str:
    """Resuelve el header ``X-Request-Origin`` al origin canónico.

    Whitelist estricta: solo ``prefetch`` y ``user``. Cualquier valor
    ausente, vacío o no permitido (incluido un ``system`` explícito del
    cliente) resuelve a ``system``. El origin ``user`` no es alcanzable
    por las rutas de producto: solo lo fuerza el endpoint de actividad.
    """
    if x_request_origin in ALLOWED_CLIENT_ORIGINS:
        return x_request_origin
    return "system"


async def log_service_interaction(
    *,
    event_id: str,
    timestamp: datetime,
    service_category: str,
    result_status: str,
    result_count: int,
    zone_ids: list[str] | None = None,
    request_mode: str | None = None,
    interaction_type: str = "request",
    origin: str = "system",
) -> None:
    """Inserta un evento de interacción con un servicio municipal.

    ``interaction_type`` (request | screen_open | filter_change) clasifica el
    tipo de evento; ``origin`` (system | prefetch | user) indica qué lo
    provocó. Ambos tienen defaults seguros para que las llamadas existentes de
    producto sigan insertando ``request/system`` sin cambios.

    Abre una sesión independiente (AsyncSessionLocal), inserta únicamente
    ServiceInteractionLog y commitea esa transacción propia. Si falla, se
    registra el error por logger y no se propaga la excepción.
    """
    if interaction_type not in INTERACTION_TYPES:
        interaction_type = "request"
    if origin not in REQUEST_ORIGINS:
        origin = "system"
    try:
        async with AsyncSessionLocal() as session:
            try:
                session.add(
                    ServiceInteractionLog(
                        event_id=event_id,
                        timestamp=timestamp,
                        service_category=service_category,
                        result_status=result_status,
                        result_count=result_count,
                        zone_ids=zone_ids or [],
                        request_mode=request_mode,
                        interaction_type=interaction_type,
                        origin=origin,
                    )
                )
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    except Exception:  # NOQA: BLE001 - telemetría secundaria
        logger.exception(
            "No se pudo registrar la interacción | event_id=%s | category=%s | status=%s",
            event_id,
            service_category,
            result_status,
        )