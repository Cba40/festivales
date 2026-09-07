from __future__ import annotations

from uuid import UUID
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from src.domain.entities.configuration_recommendation import ConfigurationRecommendation
from src.domain.entities.recommendation_enums import RecommendationStatus, RecommendationType
from src.infrastructure.persistence.models.configuration_recommendation import ConfigurationRecommendation as ConfigModel


class SQLConfigurationRecommendationRepository:
    """Repositorio para configuration_recommendations."""

    async def save(self, recommendation: ConfigurationRecommendation) -> ConfigurationRecommendation:
        async with AsyncSessionLocal() as session:
            model = ConfigModel(
                id=str(recommendation.id),
                target_entity_type=recommendation.target_entity_type,
                target_entity_id=recommendation.target_entity_id,
                proposed_change=recommendation.proposed_change,
                recommendation_type=recommendation.recommendation_type.value,
                supporting_metrics=recommendation.supporting_metrics,
                historic_trace=recommendation.historic_trace,
                recommendation_confidence=recommendation.recommendation_confidence,
                status=recommendation.status.value,
                generated_at=recommendation.generated_at,
                km_version_analyzed=str(recommendation.km_version_analyzed) if recommendation.km_version_analyzed else None,
                algorithm_version=recommendation.algorithm_version,
                event_ids=recommendation.event_ids,
                resolved_by=recommendation.resolved_by,
                resolved_at=recommendation.resolved_at,
                resolution_justification=recommendation.resolution_justification,
            )
            session.add(model)
            await session.flush()
            await session.refresh(model)
            return recommendation

    async def find_by_id(self, id: UUID) -> ConfigurationRecommendation | None:
        async with AsyncSessionLocal() as session:
            stmt = select(ConfigModel).where(ConfigModel.id == str(id))
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                return None
            
            return ConfigurationRecommendation(
                id=UUID(model.id),
                target_entity_type=model.target_entity_type,
                target_entity_id=model.target_entity_id,
                proposed_change=model.proposed_change,
                recommendation_type=RecommendationType(model.recommendation_type),
                supporting_metrics=model.supporting_metrics,
                historic_trace=model.historic_trace,
                recommendation_confidence=model.recommendation_confidence,
                status=RecommendationStatus(model.status),
                generated_at=model.generated_at,
                km_version_analyzed=UUID(model.km_version_analyzed) if model.km_version_analyzed else None,
                algorithm_version=model.algorithm_version,
                event_ids=model.event_ids,
                resolved_by=model.resolved_by,
                resolved_at=model.resolved_at,
                resolution_justification=model.resolution_justification,
            )

    async def find_all(self, status: RecommendationStatus | None = None, recommendation_type: RecommendationType | None = None) -> list[ConfigurationRecommendation]:
        async with AsyncSessionLocal() as session:
            stmt = select(ConfigModel)
            if status:
                stmt = stmt.where(ConfigModel.status == status.value)
            if recommendation_type:
                stmt = stmt.where(ConfigModel.recommendation_type == recommendation_type.value)
            
            result = await session.execute(stmt)
            models = result.scalars().all()
            
            return [
                ConfigurationRecommendation(
                    id=UUID(m.id),
                    target_entity_type=m.target_entity_type,
                    target_entity_id=m.target_entity_id,
                    proposed_change=m.proposed_change,
                    recommendation_type=RecommendationType(m.recommendation_type),
                    supporting_metrics=m.supporting_metrics,
                    historic_trace=m.historic_trace,
                    recommendation_confidence=m.recommendation_confidence,
                    status=RecommendationStatus(m.status),
                    generated_at=m.generated_at,
                    km_version_analyzed=UUID(m.km_version_analyzed) if m.km_version_analyzed else None,
                    algorithm_version=m.algorithm_version,
                    event_ids=m.event_ids,
                    resolved_by=m.resolved_by,
                    resolved_at=m.resolved_at,
                    resolution_justification=m.resolution_justification,
                )
                for m in models
            ]