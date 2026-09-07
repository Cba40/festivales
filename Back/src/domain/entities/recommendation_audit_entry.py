from __future__ import annotations

from datetime import datetime
from uuid import UUID


class RecommendationAuditEntry:
    def __init__(
        self,
        id: UUID,
        recommendation_id: UUID,
        action: str,
        timestamp: datetime,
        operator_id: str | None = None,
        justification: str | None = None,
        metrics_snapshot: dict | None = None,
        input_data_snapshot: dict | None = None,
        km_version: UUID | None = None,
        algorithm_version: str | None = None,
        llm_version: str | None = None,
    ) -> None:
        self._id = id
        self._recommendation_id = recommendation_id
        self._action = action
        self._timestamp = timestamp
        self._operator_id = operator_id
        self._justification = justification
        self._metrics_snapshot = metrics_snapshot or {}
        self._input_data_snapshot = input_data_snapshot or {}
        self._km_version = km_version
        self._algorithm_version = algorithm_version
        self._llm_version = llm_version

    # Propiedades de solo lectura
    @property
    def id(self) -> UUID:
        return self._id

    @property
    def recommendation_id(self) -> UUID:
        return self._recommendation_id

    @property
    def action(self) -> str:
        return self._action

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def operator_id(self) -> str | None:
        return self._operator_id

    @property
    def justification(self) -> str | None:
        return self._justification

    @property
    def metrics_snapshot(self) -> dict:
        return self._metrics_snapshot

    @property
    def input_data_snapshot(self) -> dict:
        return self._input_data_snapshot

    @property
    def km_version(self) -> UUID | None:
        return self._km_version

    @property
    def algorithm_version(self) -> str | None:
        return self._algorithm_version

    @property
    def llm_version(self) -> str | None:
        return self._llm_version

    def __repr__(self) -> str:
        return (
            f"RecommendationAuditEntry("
            f"id={self._id!r}, "
            f"recommendation_id={self._recommendation_id!r}, "
            f"action={self._action!r}, "
            f"timestamp={self._timestamp!r})"
        )