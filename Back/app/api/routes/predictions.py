"""Endpoint for TerritorialPrediction — invoca el Context Engine."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_token
from app.db.session import get_async_db
from app.schemas.territorial_prediction import TerritorialPrediction
from app.services.context_engine import ContextEngineService

router = APIRouter(prefix="/api/events/{event_id}", tags=["Predictions"])

engine_service = ContextEngineService()


@router.get("/prediction", response_model=TerritorialPrediction)
async def predict(
    event_id: str,
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    datetime_actual = datetime.now(timezone.utc)
    return await engine_service.predict(db, event_id, datetime_actual)
