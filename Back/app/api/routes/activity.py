"""Endpoint público de actividad (Analytics V2).

POST /api/events/{event_id}/activity

Registra ``screen_open`` y ``filter_change`` con ``origin`` forzado a ``user``.
El cliente NO elige el origin ni puede enviar ``interaction_type=request``.
Sin lógica de recomendación, sin prediction, sin Context Engine, sin PII.
La escritura reutiliza ``log_service_interaction``: si el logger falla, la
respuesta HTTP no se rompe (telemetría secundaria, igual que en los productos).
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Path

from app.schemas.activity import ActivityCreate, ActivityRecorded
from app.services.service_interaction_log import log_service_interaction

router = APIRouter(prefix="/api/events/{event_id}", tags=["Activity"])

EVENT_ID_PATTERN = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"


@router.post("/activity", response_model=ActivityRecorded, status_code=201)
async def record_activity(
    event_id: str = Path(..., pattern=EVENT_ID_PATTERN, description="ID del evento (UUID)"),
    body: ActivityCreate = Body(...),
):
    """Registra un evento de actividad de la PWA pública (anónimo)."""
    now = datetime.now(timezone.utc)
    await log_service_interaction(
        event_id=event_id,
        timestamp=now,
        service_category=body.service_category,
        result_status="ok",
        result_count=0,
        zone_ids=[],
        request_mode=body.request_mode,
        interaction_type=body.interaction_type,
        origin="user",
    )
    return ActivityRecorded(
        event_id=event_id,
        interaction_type=body.interaction_type,
        service_category=body.service_category,
        request_mode=body.request_mode,
    )