from datetime import datetime
from uuid import UUID, uuid4


class OperationalObservation:
    def __init__(
        self,
        event_day_id: UUID,
        zone_id: UUID,
        timestamp: datetime,
        observed_density: int,
        observer_id: UUID | None = None,
        source: str = "manual",
        metadata: dict | None = None,
        id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> None:
        resolved_id = id if id is not None else uuid4()
        self._validate(
            resolved_id,
            event_day_id,
            zone_id,
            timestamp,
            observed_density,
            observer_id,
            source,
        )
        self._id = resolved_id
        self._event_day_id = event_day_id
        self._zone_id = zone_id
        self._timestamp = timestamp
        self._observed_density = observed_density
        self._observer_id = observer_id
        self._source = source
        self._metadata = metadata
        self._created_at = created_at if created_at is not None else datetime.now(timestamp.tzinfo or datetime.now().astimezone().tzinfo)

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def event_day_id(self) -> UUID:
        return self._event_day_id

    @property
    def zone_id(self) -> UUID:
        return self._zone_id

    @property
    def timestamp(self) -> datetime:
        return self._timestamp

    @property
    def observed_density(self) -> int:
        return self._observed_density

    @property
    def observer_id(self) -> UUID | None:
        return self._observer_id

    @property
    def source(self) -> str:
        return self._source

    @property
    def metadata(self) -> dict | None:
        return self._metadata

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @staticmethod
    def _validate(
        id: UUID,
        event_day_id: UUID,
        zone_id: UUID,
        timestamp: datetime,
        observed_density: int,
        observer_id: UUID | None,
        source: str,
    ) -> None:
        if not isinstance(id, UUID):
            raise TypeError("id must be a UUID")
        if not isinstance(event_day_id, UUID):
            raise TypeError("event_day_id must be a UUID")
        if not isinstance(zone_id, UUID):
            raise TypeError("zone_id must be a UUID")
        if not isinstance(timestamp, datetime):
            raise TypeError("timestamp must be a datetime")
        if timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        if isinstance(observed_density, bool) or not isinstance(observed_density, int):
            raise TypeError("observed_density must be an integer")
        if observed_density < 0:
            raise ValueError("observed_density must be >= 0")
        if observer_id is not None and not isinstance(observer_id, UUID):
            raise TypeError("observer_id must be a UUID or None")
        if not isinstance(source, str):
            raise TypeError("source must be a string")
        if not source:
            raise ValueError("source must not be empty")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OperationalObservation):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return (
            f"OperationalObservation(id={self._id!r}, event_day_id={self._event_day_id!r}, "
            f"zone_id={self._zone_id!r}, timestamp={self._timestamp!r}, "
            f"observed_density={self._observed_density!r}, observer_id={self._observer_id!r}, "
            f"source={self._source!r})"
        )