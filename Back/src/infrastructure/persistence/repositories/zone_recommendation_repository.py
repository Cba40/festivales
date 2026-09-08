from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.zone_recommendation import ZoneRecommendation
from src.infrastructure.persistence.mappers.zone_recommendation_mapper import (
    zone_recommendation_to_model,
)


class SQLZoneRecommendationRepository:
    """Persiste las recomendaciones de zona emitidas al consumidor."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_batch(
        self,
        recommendations: list[ZoneRecommendation],
    ) -> None:
        if not recommendations:
            return
        self._session.add_all(
            [zone_recommendation_to_model(r) for r in recommendations]
        )
        await self._session.commit()