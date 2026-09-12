from __future__ import annotations

from uuid import UUID


from datetime import datetime

from sqlalchemy import select

from src.domain.entities.configuration_recommendation import ConfigurationRecommendation
from src.domain.entities.recommendation_audit_entry import RecommendationAuditEntry
from src.domain.entities.recommendation_enums import RecommendationStatus
from src.infrastructure.persistence.repositories.configuration_recommendation_repository import (
    SQLConfigurationRecommendationRepository,
)
from src.infrastructure.persistence.repositories.recommendation_audit_entry_repository import (
    SQLRecommendationAuditEntryRepository,
)
from src.infrastructure.notifications.stub_notification_service import StubNotificationService


class RecommendationWorkflowService:
    """Servicio que gestiona transiciones de estado estrictas de recomendaciones."""

    def __init__(
        self,
        repo: SQLConfigurationRecommendationRepository,
        audit_repo: SQLRecommendationAuditEntryRepository,
        notification_service: StubNotificationService,
    ) -> None:
        self._repo = repo
        self._audit_repo = audit_repo
        self._notification_service = notification_service

    async def create_recommendation(
        self, recommendation: ConfigurationRecommendation,
    ) -> ConfigurationRecommendation:
        """Crear nueva recomendación en estado PENDING_REVIEW."""
        from app.db.session import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            from src.infrastructure.persistence.models.configuration_recommendation import ConfigurationRecommendation as ConfigModel
            
            model = ConfigModel(
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
            )
            session.add(model)
            await session.flush()
            await session.refresh(model)

            # La BD genera el UUID (server_default=gen_random_uuid()); la entidad
            # se reconstruye con el id real persistido.
            from src.domain.entities.recommendation_enums import RecommendationType

            created = ConfigurationRecommendation(
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
            )

            # Registrar auditoría: action='generated'
            from src.infrastructure.persistence.models.recommendation_audit_entry import RecommendationAuditEntry as AuditModel

            audit_db_model = AuditModel(
                id=str(UUID()),
                recommendation_id=str(model.id),
                action="generated",
                timestamp=datetime.now(),
                operator_id=None,
                justification=None,
                km_version=model.km_version_analyzed,
                algorithm_version=model.algorithm_version,
                llm_version=None,
            )
            session.add(audit_db_model)
            await session.flush()

            # Notificar
            await self._notification_service.notify_new_recommendation(created)

            return created

    async def resolve_recommendation(
        self,
        recommendation_id: UUID,
        approved: bool,
        operator_id: str,
        justification: str | None = None,
    ) -> ConfigurationRecommendation:
        """Aprueba o rechaza una recomendación en estado PENDING_REVIEW."""
        from app.db.session import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            from src.infrastructure.persistence.models.configuration_recommendation import ConfigurationRecommendation as ConfigModel

            stmt = select(ConfigModel).where(ConfigModel.id == str(recommendation_id))
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            
            if model is None:
                raise ValueError(f"Recomendación con id {recommendation_id} no encontrada.")

            if model.status != "pending_review":
                raise ValueError(f"No se puede resolver recomendación en estado '{model.status}'.")

            # Aplicar transición
            model.status = "approved" if approved else "rejected"
            model.resolved_by = operator_id
            model.resolved_at = datetime.now()
            model.resolution_justification = justification
            
            await session.flush()

            # Registrar auditoría: action='resolved'
            from src.infrastructure.persistence.models.recommendation_audit_entry import RecommendationAuditEntry as AuditModel

            audit_db_model = AuditModel(
                id=str(UUID()),
                recommendation_id=str(model.id),
                action="resolved",
                timestamp=datetime.now(),
                operator_id=operator_id,
                justification=justification,
                km_version=model.km_version_analyzed,
                algorithm_version=model.algorithm_version,
                llm_version=None,
            )
            session.add(audit_db_model)
            await session.flush()

            # Retornar entidad de dominio actualizada
            from src.domain.entities.recommendation_enums import RecommendationType
            
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


RecommendationWorkflowServiceImpl = RecommendationWorkflowService