from datetime import datetime
from uuid import UUID, uuid4


class OperationalEvent:
    def __init__(
        self,
        target_zone_id: UUID,
        impact_value: int,
        is_incident: bool,
        start_timestamp: datetime,
        end_timestamp: datetime,
        id: UUID | None = None,
    ) -> None:
        resolved_id = id if id is not None else uuid4()
        self._validate(resolved_id, target_zone_id, impact_value, is_incident, start_timestamp, end_timestamp)
        self._id = resolved_id
        self._target_zone_id = target_zone_id
        self._impact_value = impact_value
        self._is_incident = is_incident
        self._start_timestamp = start_timestamp
        self._end_timestamp = end_timestamp

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def target_zone_id(self) -> UUID:
        return self._target_zone_id

    @property
    def impact_value(self) -> int:
        return self._impact_value

    @property
    def is_incident(self) -> bool:
        return self._is_incident

    @property
    def start_timestamp(self) -> datetime:
        return self._start_timestamp

    @property
    def end_timestamp(self) -> datetime:
        return self._end_timestamp

    @staticmethod
    def _validate(
        id: UUID,
        target_zone_id: UUID,
        impact_value: int,
        is_incident: bool,
        start_timestamp: datetime,
        end_timestamp: datetime,
    ) -> None:
        if not isinstance(id, UUID):
            raise TypeError("id must be a UUID")
        if not isinstance(target_zone_id, UUID):
            raise TypeError("target_zone_id must be a UUID")
        if isinstance(impact_value, bool) or not isinstance(impact_value, int):
            raise TypeError("impact_value must be an integer")
        if impact_value < -100 or impact_value > 100:
            raise ValueError("impact_value must be between -100 and 100")
        if not isinstance(is_incident, bool):
            raise TypeError("is_incident must be a boolean")
        if not isinstance(start_timestamp, datetime):
            raise TypeError("start_timestamp must be a datetime")
        if not isinstance(end_timestamp, datetime):
            raise TypeError("end_timestamp must be a datetime")
        if end_timestamp <= start_timestamp:
            raise ValueError("end_timestamp must be greater than start_timestamp")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OperationalEvent):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return (
            f"OperationalEvent(id={self._id!r}, target_zone_id={self._target_zone_id!r}, "
            f"impact_value={self._impact_value!r}, is_incident={self._is_incident!r}, "
            f"start_timestamp={self._start_timestamp!r}, end_timestamp={self._end_timestamp!r})"
        )
