from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from src.domain.value_objects.zone_state import ZoneState


class TerritorialPrediction:
    def __init__(
        self,
        timestamp: datetime,
        zone_states: Sequence[ZoneState],
        active_phase_id: UUID,
        active_event_day_phase_id: UUID,
        event_day_id: UUID | None = None,
        knowledge_model_version_id: UUID | None = None,
    ) -> None:
        self._timestamp = timestamp
        self._zone_states = list(zone_states)
        self._active_phase_id = active_phase_id
        self._active_event_day_phase_id = active_event_day_phase_id
        self._event_day_id = event_day_id
        self._knowledge_model_version_id = knowledge_model_version_id

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def zone_states(self) -> list[ZoneState]:
        return list(self._zone_states)

    @property
    def active_phase_id(self) -> UUID:
        return self._active_phase_id

    @property
    def active_event_day_phase_id(self) -> UUID:
        return self._active_event_day_phase_id

    @property
    def event_day_id(self) -> UUID | None:
        return self._event_day_id

    @property
    def knowledge_model_version_id(self) -> UUID | None:
        return self._knowledge_model_version_id

    def __repr__(self) -> str:
        return (
            f"TerritorialPrediction("
            f"timestamp={self._timestamp!r}, "
            f"zone_states_count={len(self._zone_states)}, "
            f"active_phase_id={self._active_phase_id!r}, "
            f"active_event_day_phase_id={self._active_event_day_phase_id!r}, "
            f"event_day_id={self._event_day_id!r}, "
            f"knowledge_model_version_id={self._knowledge_model_version_id!r})"
        )
