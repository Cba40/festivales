from __future__ import annotations

from uuid import UUID
from typing import Protocol

from src.domain.entities.configuration_recommendation import ConfigurationRecommendation


class ConfigurationRecommendationRepository(Protocol):
    async def save(self, recommendation: ConfigurationRecommendation) -> ConfigurationRecommendation: ...
    async def find_by_id(self, id: UUID) -> ConfigurationRecommendation | None: ...
    async def find_all(
        self,
        status: type | None = None,
        recommendation_type: type | None = None,
    ) -> list[ConfigurationRecommendation]: ...