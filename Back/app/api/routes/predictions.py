"""Endpoint for TerritorialPrediction — invoca el Context Engine."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_token
from app.db.session import get_async_db
from app.schemas.territorial_prediction import TerritorialPrediction as LegacyTerritorialPrediction
from app.services.context_engine import ContextEngineService
from src.interfaces.rest.predictions import get_territorial_prediction_adapter

router = APIRouter(prefix="/api/events/{event_id}", tags=["Predictions"])

engine_service = ContextEngineService()


@router.get("/prediction", response_model=LegacyTerritorialPrediction)
async def predict(
    event_id: str,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    """Endpoint protegido para Dashboard (operador)."""
    datetime_actual = datetime.now(timezone.utc)
    return await engine_service.predict(db, event_id, datetime_actual)


@router.get("/predictions")
async def get_predictions(
    event_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Endpoint público para Visitor App. No requiere autenticación."""
    timestamp = datetime.now(timezone.utc)
    prediction = await get_territorial_prediction_adapter(
        db,
        timestamp=timestamp,
        event_id=event_id,
    )
    if prediction is None:
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
            }
            for zs in prediction.zone_states
        ],
    }