from __future__ import annotations

from datetime import datetime
from uuid import UUID
from .recommendation_enums import RecommendationType, RecommendationStatus


class ConfigurationRecommendation:
    def __init__(
        self,
        id: UUID,
        target_entity_type: str,
        target_entity_id: str | None = None,
        proposed_change: str | None = None,
        recommendation_type: RecommendationType | None = None,
        supporting_metrics: dict | None = None,
        historic_trace: dict | None = None,
        recommendation_confidence: float | None = None,
        status: RecommendationStatus = RecommendationStatus.PENDING_REVIEW,
        generated_at: datetime | None = None,
        km_version_analyzed: UUID | None = None,
        algorithm_version: str | None = None,
        event_ids: list[str] | None = None,
        resolved_by: str | None = None,
        resolved_at: datetime | None = None,
        resolution_justification: str | None = None,
    ) -> None:
        self._id = id
        self._target_entity_type = target_entity_type
        self._target_entity_id = target_entity_id
        self._proposed_change = proposed_change or ""
        self._recommendation_type = recommendation_type
        self._supporting_metrics = supporting_metrics or {}
        self._historic_trace = historic_trace or {}
        self._recommendation_confidence = recommendation_confidence or 0.0
        self._status = status
        self._generated_at = generated_at or datetime.now()
        self._km_version_analyzed = km_version_analyzed
        self._algorithm_version = algorithm_version
        self._event_ids = event_ids
        self._resolved_by = resolved_by
        self._resolved_at = resolved_at
        self._resolution_justification = resolution_justification

    # Propiedades de solo lectura
    @property
    def id(self) -> UUID:
        return self._id

    @property
    def target_entity_type(self) -> str:
        return self._target_entity_type

    @property
    def target_entity_id(self) -> str | None:
        return self._target_entity_id

    @property
    def proposed_change(self) -> str:
        return self._proposed_change

    @property
    def recommendation_type(self) -> RecommendationType | None:
        return self._recommendation_type

    @property
    def supporting_metrics(self) -> dict:
        return self._supporting_metrics

    @property
    def historic_trace(self) -> dict:
        return self._historic_trace

    @property
    def recommendation_confidence(self) -> float:
        return self._recommendation_confidence

    @property
    def status(self) -> RecommendationStatus:
        return self._status

    @property
    def generated_at(self) -> datetime:
        return self._generated_at

    @property
    def km_version_analyzed(self) -> UUID | None:
        return self._km_version_analyzed

    @property
    def algorithm_version(self) -> str | None:
        return self._algorithm_version

    @property
    def event_ids(self) -> list[str] | None:
        return self._event_ids

    @property
    def resolved_by(self) -> str | None:
        return self._resolved_by

    @property
    def resolved_at(self) -> datetime | None:
        return self._resolved_at

    @property
    def resolution_justification(self) -> str | None:
        return self._resolution_justification

    # Métodos de transición de estado
    def approve(self, operator_id: str, justification: str | None = None) -> None:
        if self._status != RecommendationStatus.PENDING_REVIEW:
            raise ValueError(
                f"No se puede aprobar recomendación en estado '{self._status.value}'. "
                "Solo se pueden aprobar recomendaciones con estado 'pending_review'."
            )
        self._status = RecommendationStatus.APPROVED
        self._resolved_by = operator_id
        self._resolved_at = datetime.now()
        self._resolution_justification = justification

    def reject(self, operator_id: str, justification: str | None = None) -> None:
        if self._status != RecommendationStatus.PENDING_REVIEW:
            raise ValueError(
                f"No se puede rechazar recomendación en estado '{self._status.value}'. "
                "Solo se pueden rechazar recomendaciones con estado 'pending_review'."
            )
        self._status = RecommendationStatus.REJECTED
        self._resolved_by = operator_id
        self._resolved_at = datetime.now()
        self._resolution_justification = justification

    def __repr__(self) -> str:
        return (
            f"ConfigurationRecommendation("
            f"id={self._id!r}, "
            f"target_entity_type={self._target_entity_type!r}, "
            f"recommendation_type={self._recommendation_type!r}, "
            f"status={self._status.value!r}, "
            f"recommendation_confidence={self._recommendation_confidence!r}, "
            f"generated_at={self._generated_at!r})"
        )

    # Validación interna
    def is_pending(self) -> bool:
        return self._status == RecommendationStatus.PENDING_REVIEW

    def is_approved(self) -> bool:
        return self._status == RecommendationStatus.APPROVED

    def is_rejected(self) -> bool:
        return self._status == RecommendationStatus.REJECTED