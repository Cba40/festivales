from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.config import settings
from app.db.session import get_async_db, AsyncSessionLocal as async_session_maker
from app.schemas.configuration_recommendation import (
    ConfigurationRecommendationCreate,
    ConfigurationRecommendationResponse,
    ResolveRecommendationRequest,
)
from src.infrastructure.persistence.models.configuration_recommendation import (
    ConfigurationRecommendation as ConfigModel,
)
from src.infrastructure.persistence.models.recommendation_audit_entry import (
    RecommendationAuditEntry as AuditModel,
)
from src.infrastructure.persistence.repositories.configuration_recommendation_repository import (
    SQLConfigurationRecommendationRepository,
)
from src.infrastructure.persistence.repositories.recommendation_audit_entry_repository import (
    SQLRecommendationAuditEntryRepository,
)
from src.application.learning.workflow_service import (
    RecommendationWorkflowServiceImpl,
)
from src.infrastructure.notifications.stub_notification_service import (
    StubNotificationService,
)
from src.domain.ports.configuration_recommendation_repository import (
    ConfigurationRecommendationRepository,
)
from uuid import UUID
from datetime import datetime


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


async def _get_workflow_service(session: AsyncSession):
    repo = SQLConfigurationRecommendationRepository()
    audit_repo = SQLRecommendationAuditEntryRepository()
    notification_service = StubNotificationService()
    return RecommendationWorkflowServiceImpl(
        repo=repo,
        audit_repo=audit_repo,
        notification_service=notification_service,
)


@router.post(
    "/recommendations",
    response_model=ConfigurationRecommendationResponse,
    status_code=201,
)
async def create_recommendation(
    recommendation_in: ConfigurationRecommendationCreate,
    db: AsyncSession = Depends(get_async_db),
):
    """Crear nueva recomendación en estado PENDING_REVIEW."""
    async with async_session_maker() as session:
        workflow = await _get_workflow_service(session)

        from src.domain.entities.configuration_recommendation import (
            ConfigurationRecommendation as DomainRec,
        )

        recommendation = ConfigModel(
            id=UUID(),
            target_entity_type=recommendation_in.target_entity_type,
            target_entity_id=recommendation_in.target_entity_id or None,
            proposed_change=recommendation_in.proposed_change,
            recommendation_type=recommendation_in.recommendation_type.value
            if recommendation_in.recommendation_type
            else None,
            supporting_metrics=recommendation_in.supporting_metrics,
            historic_trace=recommendation_in.historic_trace,
            recommendation_confidence=recommendation_in.recommendation_confidence,
            event_ids=recommendation_in.event_ids or None,
            km_version_analyzed=recommendation_in.km_version_analyzed,
            algorithm_version=recommendation_in.algorithm_version,
        )

        domain_rec = DomainRec(
            id=UUID(),
            target_entity_type=recommendation_in.target_entity_type,
            target_entity_id=recommendation_in.target_entity_id or None,
            proposed_change=recommendation_in.proposed_change,
            recommendation_type=recommendation_in.recommendation_type,
            supporting_metrics=recommendation_in.supporting_metrics,
            historic_trace=recommendation_in.historic_trace,
            recommendation_confidence=recommendation_in.recommendation_confidence,
            status="pending_review",
            generated_at=datetime.now(),
            km_version_analyzed=recommendation_in.km_version_analyzed,
            algorithm_version=recommendation_in.algorithm_version,
            event_ids=recommendation_in.event_ids or None,
            resolved_by=None,
            resolved_at=None,
            resolution_justification=None,
        )

        result = await workflow.create_recommendation(domain_rec)
        return result


@router.get(
    "/recommendations",
    response_model=List[ConfigurationRecommendationResponse],
)
async def list_recommendations(
    status: Optional[str] = None,
    recommendation_type: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """Listar recomendaciones con filtros opcionales."""
    async with async_session_maker() as session:
        from src.infrastructure.persistence.models.configuration_recommendation import (
            ConfigurationRecommendation as M,
        )

        stmt = select(M)
        if status is not None:
            stmt = stmt.where(M.status == status)
        if recommendation_type is not None:
            stmt = stmt.where(M.recommendation_type == recommendation_type)
        result = await session.execute(stmt)
        models = result.scalars().all()

        from app.schemas.configuration_recommendation import (
            ConfigurationRecommendationResponse,
        )

        return [
            ConfigurationRecommendationResponse(
                id=str(m.id),
                target_entity_type=m.target_entity_type,
                target_entity_id=m.target_entity_id,
                proposed_change=m.proposed_change or "",
                recommendation_type=(
                    type(m.recommendation_type).__name__ if m.recommendation_type else None
                ),
                supporting_metrics=m.supporting_metrics,
                historic_trace=m.historic_trace,
                recommendation_confidence=m.recommendation_confidence,
                status=type(m.status).__name__ if m.status else "pending_review",
                generated_at=m.generated_at,
                km_version_analyzed=m.km_version_analyzed,
                algorithm_version=m.algorithm_version,
                event_ids=m.event_ids or None,
                resolved_by=m.resolved_by,
                resolved_at=m.resolved_at,
                resolution_justification=m.resolution_justification or None,
            )
            for m in models
        ]


@router.get(
    "/recommendations/{id}",
    response_model=ConfigurationRecommendationResponse,
)
async def get_recommendation(
    id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Detalle de una recomendación por ID."""
    async with async_session_maker() as session:
        from src.infrastructure.persistence.models.configuration_recommendation import (
            ConfigurationRecommendation as M,
        )

        stmt = select(M).where(M.id == UUID(id))
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Recomendación no encontrada")

        from app.schemas.configuration_recommendation import (
            ConfigurationRecommendationResponse,
        )

        return ConfigurationRecommendationResponse(
            id=str(model.id),
            target_entity_type=model.target_entity_type,
            target_entity_id=model.target_entity_id,
            proposed_change=model.proposed_change or "",
            recommendation_type=(
                type(model.recommendation_type).__name__ if model.recommendation_type else None
            ),
            supporting_metrics=model.supporting_metrics,
            historic_trace=model.historic_trace,
            recommendation_confidence=model.recommendation_confidence,
            status=type(model.status).__name__ if model.status else "pending_review",
            generated_at=model.generated_at,
            km_version_analyzed=model.km_version_analyzed,
            algorithm_version=model.algorithm_version,
            event_ids=model.event_ids or None,
            resolved_by=model.resolved_by,
            resolved_at=model.resolved_at,
            resolution_justification=model.resolution_justification or None,
        )


@router.post(
    "/recommendations/{id}/resolve",
    response_model=ConfigurationRecommendationResponse,
)
async def resolve_recommendation(
    id: str,
    request: ResolveRecommendationRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """Aprueba o rechaza una recomendación."""
    async with async_session_maker() as session:
        from src.infrastructure.persistence.models.configuration_recommendation import (
            ConfigurationRecommendation as M,
        )
        from src.infrastructure.persistence.models.recommendation_audit_entry import (
            RecommendationAuditEntry as AuditM,
        )
        from uuid import UUID
        from datetime import datetime

        stmt = select(M).where(M.id == UUID(id))
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Recomendación no encontrada")

        from src.application.learning.workflow_service import (
            RecommendationWorkflowServiceImpl,
        )
        from src.infrastructure.notifications.stub_notification_service import (
            StubNotificationService,
        )
        from src.domain.ports.configuration_recommendation_repository import (
            ConfigurationRecommendationRepository,
        )
        from src.infrastructure.persistence.repositories.configuration_recommendation_repository import (
            SQLConfigurationRecommendationRepository,
        )

        repo = SQLConfigurationRecommendationRepository()
        audit_repo = SQLRecommendationAuditEntryRepository()
        notification_svc = StubNotificationService()
        workflow = RecommendationWorkflowServiceImpl(
            repo=repo,
            audit_repo=audit_repo,
            notification_service=notification_svc,
        )

        recommendation = ConfigModel(
            id=UUID(id),
            target_entity_type=model.target_entity_type,
            target_entity_id=model.target_entity_id,
            proposed_change=model.proposed_change or "",
            recommendation_type=type(model.recommendation_type).__name__
            if model.recommendation_type
            else None,
            supporting_metrics=model.supporting_metrics,
            historic_trace=model.historic_trace,
            recommendation_confidence=model.recommendation_confidence,
            status=type(model.status).__name__ if model.status else "pending_review",
            generated_at=model.generated_at,
            km_version_analyzed=model.km_version_analyzed,
            algorithm_version=model.algorithm_version,
            event_ids=model.event_ids or None,
            resolved_by=model.resolved_by,
            resolved_at=model.resolved_at,
            resolution_justification=model.resolution_justification or None,
        )

        result = await workflow.resolve_recommendation(
            id=UUID(id),
            approved=request.approved,
            operator_id=request.operator_id,
            justification=request.justification,
        )
        return result


@router.get(
    "/audit-log",
    response_model=List[dict],
)
async def get_audit_log(
    recommendation_id: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
):
    """Consultar registro de auditoría."""
    async with async_session_maker() as session:
        from src.infrastructure.persistence.models.recommendation_audit_entry import (
            RecommendationAuditEntry as M,
        )

        stmt = select(M)
        if recommendation_id is not None:
            stmt = stmt.where(M.recommendation_id == recommendation_id)
        result = await session.execute(stmt)
        models = result.scalars().all()

        return [
            {
                "id": str(m.id),
                "recommendation_id": str(m.recommendation_id),
                "action": m.action,
                "timestamp": m.timestamp.isoformat() if m.timestamp else None,
                "operator_id": m.operator_id,
                "justification": m.justification,
                "km_version": str(m.km_version) if m.km_version else None,
                "algorithm_version": m.algorithm_version,
                "llm_version": m.llm_version,
            }
            for m in models
        ]