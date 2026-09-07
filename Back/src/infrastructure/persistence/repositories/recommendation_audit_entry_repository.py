from __future__ import annotations

from uuid import UUID
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from src.domain.entities.recommendation_audit_entry import RecommendationAuditEntry
from src.infrastructure.persistence.models.recommendation_audit_entry import RecommendationAuditEntry as AuditModel


class SQLRecommendationAuditEntryRepository:
    """Repositorio append-only para recommendation_audit_log."""

    async def save(self, entry: RecommendationAuditEntry) -> RecommendationAuditEntry:
        async with AsyncSessionLocal() as session:
            model = AuditModel(
                id=str(entry.id),
                recommendation_id=str(entry.recommendation_id),
                action=entry.action,
                timestamp=entry.timestamp,
                operator_id=entry.operator_id,
                justification=entry.justification,
                metrics_snapshot=entry.metrics_snapshot,
                input_data_snapshot=entry.input_data_snapshot,
                km_version=str(entry.km_version) if entry.km_version else None,
                algorithm_version=entry.algorithm_version,
                llm_version=entry.llm_version,
            )
            session.add(model)
            await session.flush()
            await session.refresh(model)
            return entry

    async def find_by_recommendation_id(self, recommendation_id: UUID) -> list[RecommendationAuditEntry]:
        async with AsyncSessionLocal() as session:
            stmt = select(AuditModel).where(AuditModel.recommendation_id == str(recommendation_id))
            result = await session.execute(stmt)
            models = result.scalars().all()
            
            return [
                RecommendationAuditEntry(
                    id=UUID(m.id),
                    recommendation_id=UUID(m.recommendation_id),
                    action=m.action,
                    timestamp=m.timestamp,
                    operator_id=m.operator_id,
                    justification=m.justification,
                    metrics_snapshot=m.metrics_snapshot,
                    input_data_snapshot=m.input_data_snapshot,
                    km_version=UUID(m.km_version) if m.km_version else None,
                    algorithm_version=m.algorithm_version,
                    llm_version=m.llm_version,
                )
                for m in models
            ]