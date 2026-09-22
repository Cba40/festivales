"""Public combined endpoint for transport alerts and operator messages (RFC-ALERTS-MESSAGES-V1).

Expone las alertas activas y los mensajes publicados de un evento en una sola
respuesta, ordenados por severidad (alertas: disruption > closure > warning >
info; mensajes: urgent > high > normal). Utiliza la zona horaria de Argentina
para calcular la ventana temporal vigente.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.operator_message import list_active as list_active_messages
from app.crud.transport_alert import list_active as list_active_alerts
from app.db.session import get_async_db

ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

SEVERITY_ORDER = {"disruption": 0, "closure": 1, "warning": 2, "info": 3}
PRIORITY_ORDER = {"urgent": 0, "high": 1, "normal": 2}

router = APIRouter(prefix="/api/events/{event_id}", tags=["Alerts Product"])


class PublicAlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    line_id: Optional[str]
    alert_type: str
    title: str
    description: str
    valid_from: datetime
    valid_until: datetime


class PublicMessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    line_id: Optional[str]
    priority: str
    title: str
    description: str
    publish_at: datetime
    expires_at: Optional[datetime]


class PublicAlertsResponse(BaseModel):
    alerts: list[PublicAlertItem]
    messages: list[PublicMessageItem]


@router.get("/alerts", response_model=PublicAlertsResponse)
async def get_public_alerts(
    event_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    now = datetime.now(ARGENTINA_TZ)
    alerts = await list_active_alerts(db, event_id, now)
    messages = await list_active_messages(db, event_id, now)

    alerts.sort(key=lambda a: SEVERITY_ORDER.get(a.alert_type, 3))
    messages.sort(key=lambda m: PRIORITY_ORDER.get(m.priority, 2))

    return PublicAlertsResponse(alerts=alerts, messages=messages)