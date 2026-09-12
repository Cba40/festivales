import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.api.deps import TokenPayload, verify_token
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
from src.application.learning.anomaly_detector import Anomaly, AnomalyDetector
from src.application.learning.metric_service import MetricService
from src.domain.entities.configuration_recommendation import (
    ConfigurationRecommendation,
)
from src.domain.entities.recommendation_enums import (
    RecommendationStatus,
    RecommendationType,
)
from app.models.event_day import EventDay
from app.models.operational_phase import OperationalPhase
from src.infrastructure.composition.prediction_module import PredictionModule
from app.schemas.analytics import (
    AnomalyResponse,
    EvaluationRequest,
    EvaluationResponse,
    MetricResultResponse,
    RecommendationCreatedResponse,
)
from uuid import UUID
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class MetricsStatusResponse(BaseModel):
    density_deviation: str
    incident_frequency: str
    phase_transition_latency: str
    zone_behavior_adherence: str


router = APIRouter(prefix="/api/analytics", tags=["analytics"])


async def _get_metrics_status(session: AsyncSession) -> MetricsStatusResponse:
    from sqlalchemy import text

    async def _count(table: str, where: str = "") -> tuple[bool, int]:
        sql = f"SELECT COUNT(*) FROM {table}" + (f" WHERE {where}" if where else "")
        try:
            result = await session.execute(text(sql))
            return True, int(result.scalar_one())
        except Exception:
            return False, 0

    # 1. Desviación de Densidad: predictions + operational_observations
    pred_ok, pred_count = await _count("predictions")
    obs_ok, obs_count = await _count("operational_observations")
    if not pred_ok or not obs_ok:
        density_status = (
            "BLOQUEADA — la tabla predictions o operational_observations no existe en la BD."
        )
    elif obs_count == 0:
        density_status = "BLOQUEADA — 0 observaciones reales de densidad para contrastar"
    elif pred_count == 0:
        density_status = "BLOQUEADA — no hay predicciones históricas de densidad para contrastar"
    else:
        density_status = (
            f"HABILITADA — {obs_count} observaciones de densidad reales "
            f"para contrastar contra {pred_count} predicciones"
        )

    # 2. Frecuencia de Incidentes: operational_events con is_incident=true
    events_ok, events_count = await _count("operational_events")
    if not events_ok:
        incident_status = "LIMITADA — la tabla operational_events no existe en la BD."
    elif events_count == 0:
        incident_status = "LIMITADA — 0 eventos registrados sobre los que calcular la frecuencia"
    else:
        _, incidents_count = await _count("operational_events", "is_incident = true")
        if incidents_count == 0:
            incident_status = f"LIMITADA — solo {events_count} eventos, 0 incidents reales"
        else:
            incident_status = (
                f"HABILITADA — {events_count} eventos con "
                f"{incidents_count} incidents reales"
            )

    # 3. Latencia de Transición de Fases: siempre bloqueada por RFC-006
    latency_status = (
        "BLOQUEADA — no existe actualmente una fuente de observación de transición "
        "de fase definida. No se modifica operational_events en esta fase."
    )

    # 4. Adherencia a ZoneBehavior: operational_observations + zone_behaviors
    obs2_ok, obs2_count = await _count("operational_observations")
    behaviors_ok, behaviors_count = await _count("zone_behaviors")
    if not obs2_ok:
        adherence_status = "BLOQUEADA — requiere la tabla operational_observations (ausente)."
    elif not behaviors_ok:
        adherence_status = "BLOQUEADA — requiere la tabla zone_behaviors (ausente)."
    elif obs2_count == 0:
        adherence_status = (
            "BLOQUEADA — requiere operational_observations (actualmente 0 registros)."
        )
    elif behaviors_count == 0:
        adherence_status = (
            "BLOQUEADA — requiere reference en zone_behaviors (actualmente 0 registros)."
        )
    else:
        adherence_status = (
            f"HABILITADA — {obs2_count} observaciones para contrastar contra "
            f"{behaviors_count} ZoneBehavior de referencia"
        )

    return MetricsStatusResponse(
        density_deviation=density_status,
        incident_frequency=incident_status,
        phase_transition_latency=latency_status,
        zone_behavior_adherence=adherence_status,
    )


@router.get(
    "/metrics-status",
    response_model=MetricsStatusResponse,
)
async def get_metrics_status(
    db: AsyncSession = Depends(get_async_db),
):
    """Endpoint de estado de métricas RFC-006 §5 (solo lectura)."""
    async with async_session_maker() as session:
        return await _get_metrics_status(session)


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
                recommendation_type=m.recommendation_type if m.recommendation_type else None,
                supporting_metrics=m.supporting_metrics,
                historic_trace=m.historic_trace,
                recommendation_confidence=m.recommendation_confidence,
                status=m.status if m.status else "pending_review",
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
            recommendation_type=model.recommendation_type if model.recommendation_type else None,
            supporting_metrics=model.supporting_metrics,
            historic_trace=model.historic_trace,
            recommendation_confidence=model.recommendation_confidence,
            status=model.status if model.status else "pending_review",
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
            recommendation_type=model.recommendation_type
            if model.recommendation_type
            else None,
            supporting_metrics=model.supporting_metrics,
            historic_trace=model.historic_trace,
            recommendation_confidence=model.recommendation_confidence,
            status=model.status if model.status else "pending_review",
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


def _build_recommendation(
    anomaly: Anomaly,
    request: EvaluationRequest,
) -> ConfigurationRecommendation:
    """Construye una ConfigurationRecommendation en estado PENDING_REVIEW."""
    return ConfigurationRecommendation(
        target_entity_type="event_day",
        target_entity_id=request.event_day_id,
        proposed_change=anomaly.suggested_action,
        recommendation_type=RecommendationType.PARAMETER_ADJUSTMENT,
        supporting_metrics={
            "metric": anomaly.metric_name,
            "value": anomaly.value,
            "phase_id": request.phase_id,
        },
        historic_trace={
            "event_day_id": request.event_day_id,
            "phase_id": request.phase_id,
        },
        recommendation_confidence=0.9,
        status=RecommendationStatus.PENDING_REVIEW,
        km_version_analyzed=None,
        algorithm_version="etapa2-v1",
        event_ids=None,
    )


async def _capture_prediction(
    session: AsyncSession,
    event_id: str,
    timestamp: datetime,
) -> None:
    """Genera y persiste una predicción para la evaluación L&A (Camino A).

    PredictionModule(persist=True) ejecuta el flujo completo y delega el save
    (flush sin commit) a SQLPredictionRepository; el commit y el rollback
    pertenecen a este servicio coordinador.
    """
    try:
        prediction = await PredictionModule(session).execute(
            timestamp=timestamp,
            event_id=event_id,
            persist=True,
        )
    except Exception:
        await session.rollback()
        raise
    if prediction is None:
        logger.warning(
            "L&A capture: no se pudo generar predicción (event_id=%s); "
            "las métricas que dependen de predicciones quedarán BLOCKED.",
            event_id,
        )
    await session.commit()


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_metrics(
    request: EvaluationRequest,
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    """Ejecuta el MetricService, detecta anomalías y crea recomendaciones (Etapa 2)."""
    logger.info(
        "evaluate_metrics event_day_id=%s phase_id=%s",
        request.event_day_id,
        request.phase_id,
    )

    # 1. Validar que event_day y phase existan
    day_row = (
        await db.execute(select(EventDay).where(EventDay.id == request.event_day_id))
    ).scalar_one_or_none()
    if day_row is None:
        raise HTTPException(status_code=404, detail="EventDay no encontrado")

    try:
        phase_uuid = UUID(request.phase_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Phase no encontrada")

    phase_result = await db.execute(
        select(OperationalPhase).where(OperationalPhase.id == phase_uuid)
    )
    if phase_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Phase no encontrada")

    # 2. Capturar una predicción persistible para la evaluación L&A (Camino A)
    try:
        await _capture_prediction(
            db,
            event_id=day_row.event_id,
            timestamp=datetime.now(timezone.utc),
        )
    except Exception as exc:
        logger.exception(
            "Fallo al capturar predicción en evaluación L&A: %s", exc
        )
        raise HTTPException(
            status_code=500,
            detail="Error interno al capturar predicción para la evaluación",
        )

    # 3. Ejecutar MetricService.calculate_all
    #    phase_id alineado: el mismo UUID validado en OperationalPhase se pasa en
    #    forma canónica; MetricService filtra ZoneBehaviorModel.operational_phase_id.
    try:
        results = await MetricService(db).calculate_all(
            request.event_day_id,
            str(phase_uuid),
        )
    except Exception as exc:
        logger.exception("Fallo en MetricService.calculate_all: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Error interno al evaluar métricas",
        )

    metrics = [
        MetricResultResponse(
            name=r.name,
            display_name=r.display_name,
            status=r.status,
            value=r.value,
            reason=r.reason,
            data_points=r.data_points,
            limitations=r.limitations or [],
            is_provisional=r.is_provisional,
        )
        for r in results
    ]

    # 5. Detectar anomalías
    anomalies = AnomalyDetector().detect_all(results)

    # 6. Crear una recomendación por anomalía; un fallo individual no rompe el flujo
    workflow_service = await _get_workflow_service(db)
    recommendations_created: list[RecommendationCreatedResponse] = []
    for anomaly in anomalies:
        try:
            created = await workflow_service.create_recommendation(
                _build_recommendation(anomaly, request)
            )
            recommendations_created.append(
                RecommendationCreatedResponse(
                    id=str(created.id),
                    status=(
                        created.status.value
                        if created.status
                        else RecommendationStatus.PENDING_REVIEW.value
                    ),
                    metric_name=anomaly.metric_name,
                )
            )
        except Exception as exc:
            logger.exception(
                "Fallo al crear recomendación para %s: %s",
                anomaly.metric_name,
                exc,
            )
            continue

    # 7. Resumen completo
    return EvaluationResponse(
        metrics=metrics,
        anomalies_detected=len(anomalies),
        anomalies=[AnomalyResponse(**asdict(a)) for a in anomalies],
        recommendations_created=recommendations_created,
    )