"""Endpoint for TerritorialPrediction — invoca el Context Engine."""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import verify_token
from app.db.session import get_async_db
from app.models.attendance_level import AttendanceLevel
from app.models.event import Event
from app.models.event_day import EventDay
from app.models.operational_profile import OperationalProfile
from app.models.zone import Zone
from src.interfaces.rest.predictions import get_territorial_prediction_adapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events/{event_id}", tags=["Predictions"])


async def _collect_prediction_debug_state(
    db: AsyncSession,
    event_id: str,
    timestamp: datetime,
    prediction: object | None,
) -> str:
    """P3.1E debug: registra estado del endpoint y devuelve la condicion del 404."""
    event_row = (
        await db.execute(select(Event).where(Event.id == event_id))
    ).scalar_one_or_none()

    zone_rows = (
        await db.execute(select(Zone).where(Zone.event_id == event_id))
    ).scalars().all()

    ed_row = (
        await db.execute(
            select(EventDay)
            .where(EventDay.date == timestamp.date())
            .options(selectinload(EventDay.phases))
        )
    ).scalar_one_or_none()

    attendance_row = None
    profile_row = None
    if ed_row is not None:
        attendance_row = (
            await db.execute(
                select(AttendanceLevel).where(
                    AttendanceLevel.id == ed_row.attendance_level_id,
                )
            )
        ).scalar_one_or_none()
        profile_row = (
            await db.execute(
                select(OperationalProfile).where(
                    OperationalProfile.id == ed_row.operational_profile_id,
                )
            )
        ).scalar_one_or_none()

    logger.info(
        "[PREDICTION DEBUG] event_id=%s timestamp_recibido=%s | event=%s | "
        "event_day=%s | event_day_phases=%d | zones=%d | "
        "attendance_level=%s | operational_profile=%s | result=%s",
        event_id,
        timestamp.isoformat(),
        {"id": event_row.id, "name": event_row.name} if event_row else None,
        (
            {
                "id": ed_row.id,
                "operational_profile_id": str(ed_row.operational_profile_id),
                "attendance_level_id": ed_row.attendance_level_id,
                "operational_start_min": ed_row.operational_start_min,
                "operational_end_min": ed_row.operational_end_min,
            }
            if ed_row
            else None
        ),
        len(ed_row.phases) if ed_row else 0,
        len(zone_rows),
        bool(attendance_row),
        bool(profile_row),
        "prediction == None" if prediction is None else "prediction generado correctamente",
    )

    if ed_row is not None and ed_row.phases:
        for phase in ed_row.phases:
            logger.info(
                "[PREDICTION DEBUG] phase operational_phase_id=%s start_min=%s end_min=%s",
                phase.operational_phase_id,
                phase.start_min,
                phase.end_min,
            )

    for zone in zone_rows:
        logger.info(
            "[PREDICTION DEBUG] zone id=%s name=%s type=%s status=%s",
            zone.id,
            zone.name,
            zone.type,
            zone.status,
        )

    if prediction is not None:
        return "ok"
    if not zone_rows:
        return "zones_empty"
    if ed_row is None:
        return "no_event_day"
    if attendance_row is None:
        return "no_attendance_level"
    if profile_row is None:
        return "no_operational_profile"
    if not ed_row.phases:
        return "no_active_phase"
    return "adapter_returned_none"


async def _log_prediction_debug(
    db: AsyncSession,
    event_id: str,
    timestamp: datetime,
    prediction: object | None,
) -> str:
    """P3.1E debug: solo diagnostico, nunca altera la respuesta del endpoint."""
    try:
        return await _collect_prediction_debug_state(db, event_id, timestamp, prediction)
    except Exception as exc:  # pragma: no cover
        logger.error(
            "[PREDICTION DEBUG] estado no disponible | event_id=%s | timestamp=%s | error=%s",
            event_id,
            timestamp.isoformat(),
            exc,
        )
        return "adapter_returned_none" if prediction is None else "ok"


async def _build_prediction_response(
    db: AsyncSession,
    event_id: str,
    timestamp: datetime,
) -> dict:
    prediction = await get_territorial_prediction_adapter(
        db,
        timestamp=timestamp,
        event_id=event_id,
    )
    reason = await _log_prediction_debug(db, event_id, timestamp, prediction)
    if prediction is None:
        logger.error(
            "[PREDICTION DEBUG] reason=%s | event_id=%s | timestamp=%s",
            reason,
            event_id,
            timestamp.isoformat(),
        )
        raise HTTPException(
            status_code=404,
            detail="No se encontraron zonas para el evento o datos insuficientes para generar predicción.",
        )
    return {
        "timestamp": prediction.timestamp.isoformat(),
        "active_phase_id": str(prediction.active_phase_id),
        "active_event_day_phase_id": str(prediction.active_event_day_phase_id),
        "zone_states": [
            {
                "zone_id": str(zs.zone_id),
                "operational_state": zs.operational_state,
                "availability": zs.availability,
                "saturation_level": zs.saturation_level,
                "estimated_wait": zs.estimated_wait,
                "confidence": zs.confidence,
                "reasoning_factors": list(zs.reasoning_factors),
                "active_restriction": zs.active_restriction.value,
                "type": zs.type,
                "subtipo": zs.subtipo,
            }
            for zs in prediction.zone_states
        ],
    }


@router.get("/prediction")
async def predict(
    event_id: str,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    """Endpoint protegido para Dashboard (operador)."""
    timestamp = datetime.now(timezone.utc)
    return await _build_prediction_response(db, event_id, timestamp)


@router.get("/predictions")
async def get_predictions(
    event_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Endpoint público para Visitor App. No requiere autenticación."""
    timestamp = datetime.now(timezone.utc)
    try:
        return await _build_prediction_response(db, event_id, timestamp)
    except Exception:
        logger.exception(
            "Prediction endpoint failed | event_id=%s",
            event_id,
        )
        raise