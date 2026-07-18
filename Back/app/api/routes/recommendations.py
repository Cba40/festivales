from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import verify_token
from app.db.session import get_async_db
from app.schemas.recommendation import RecommendationResponse, ZoneRecommendationItem
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import ActionType, RequestedAction
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.interfaces.rest.recommendations import get_recommendations_adapter

router = APIRouter(prefix="/api/events/{event_id}", tags=["Recommendations"])


@router.get("/recommendations", response_model=RecommendationResponse)
async def recommend(
    event_id: str,
    access_level: AccessLevel = Query(...),
    action_type: ActionType = Query(...),
    speed: float = Query(..., ge=0.0),
    accessibility_required: bool = Query(...),
    limit: int = Query(5, ge=1, le=50),
    current_zone_id: str | None = Query(None),
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_async_db),
    _=Depends(verify_token),
):
    now = datetime.now(timezone.utc)

    user_ctx = UserContext(
        user_id=UUID(user_id),
        access_level=access_level,
    )
    mobility_ctx = MobilityContext(
        current_zone_id=UUID(current_zone_id) if current_zone_id else None,
        speed=speed,
        accessibility_required=accessibility_required,
    )
    requested_action = RequestedAction(action_type=action_type)

    recs, prediction = await get_recommendations_adapter(
        db=db,
        timestamp=now,
        event_id=event_id,
        user_context=user_ctx,
        mobility_context=mobility_ctx,
        requested_action=requested_action,
        limit=limit,
    )

    if prediction is None:
        raise HTTPException(status_code=500, detail="No se pudo generar la predicción")

    return RecommendationResponse(
        event_id=event_id,
        timestamp=prediction.timestamp.isoformat(),
        recommendations=[
            ZoneRecommendationItem(
                zone_id=str(r.zone_id),
                score=r.score,
                reasoning=r.reasoning,
            )
            for r in recs
        ],
    )
