from __future__ import annotations

from datetime import datetime
from uuid import UUID


class OperationalObservation:
    def __init__(
        self,
        id: UUID,
        event_day_id: str,
        zone_id: str,
        timestamp: datetime,
        observed_density: int,
        observer_id: str | None = None,
        source: str = "manual",
        metadata: dict | None = None,
        created_at: datetime | None = None,
    ) -> None:
        self._id = id
        self._event_day_id = event_day_id
        self._zone_id = zone_id
        self._timestamp = timestamp
        self._observed_density = observed_density
        self._observer_id = observer_id
        self._source = source
        self._metadata = metadata or {}
        self._created_at = created_at or datetime.now()

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def event_day_id(self) -> str:
        return self._event_day_id

    @property
    def zone_id(self) -> str:
        return self._zone_id

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def observed_density(self) -> int:
        return self._observed_density

    @property
    def observer_id(self) -> str | None:
        return self._observer_id

    @property
    def source(self) -> str:
        return self._source

    @property
    def metadata(self) -> dict:
        return self._metadata

    @property
    def created_at(self) -> datetime | None:
        return self._created_at

    def __repr__(self) -> str:
        return (
            f"OperationalObservation("
            f"id={self._id!r}, "
            f"event_day_id={self._event_day_id!r}, "
            f"zone_id={self._zone_id!r}, "
            f"observed_density={self._observed_density!r}, "
            f"source={self._source!r})"
        )