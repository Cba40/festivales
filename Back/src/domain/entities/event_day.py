from datetime import date
from uuid import UUID, uuid4


class EventDay:
    def __init__(
        self,
        event_date: date,
        operational_profile_id: UUID,
        attendance_level_id: UUID,
        operational_start_min: int,
        operational_end_min: int,
        id: UUID | None = None,
    ) -> None:
        resolved_id = id if id is not None else uuid4()
        self._validate(
            resolved_id,
            event_date,
            operational_profile_id,
            attendance_level_id,
            operational_start_min,
            operational_end_min,
        )
        self._id = resolved_id
        self._event_date = event_date
        self._operational_profile_id = operational_profile_id
        self._attendance_level_id = attendance_level_id
        self._operational_start_min = operational_start_min
        self._operational_end_min = operational_end_min

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def event_date(self) -> date:
        return self._event_date

    @property
    def operational_profile_id(self) -> UUID:
        return self._operational_profile_id

    @property
    def attendance_level_id(self) -> UUID:
        return self._attendance_level_id

    @property
    def operational_start_min(self) -> int:
        return self._operational_start_min

    @property
    def operational_end_min(self) -> int:
        return self._operational_end_min

    @staticmethod
    def _validate(
        id: UUID,
        event_date: date,
        operational_profile_id: UUID,
        attendance_level_id: UUID,
        operational_start_min: int,
        operational_end_min: int,
    ) -> None:
        if not isinstance(id, UUID):
            raise TypeError("id must be a UUID")
        if not isinstance(event_date, date):
            raise TypeError("event_date must be a date")
        if not isinstance(operational_profile_id, UUID):
            raise TypeError("operational_profile_id must be a UUID")
        if not isinstance(attendance_level_id, UUID):
            raise TypeError("attendance_level_id must be a UUID")
        if isinstance(operational_start_min, bool) or not isinstance(operational_start_min, int):
            raise TypeError("operational_start_min must be an integer")
        if operational_start_min < 0:
            raise ValueError("operational_start_min must be >= 0")
        if isinstance(operational_end_min, bool) or not isinstance(operational_end_min, int):
            raise TypeError("operational_end_min must be an integer")
        if operational_end_min <= operational_start_min:
            raise ValueError("operational_end_min must be greater than operational_start_min")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EventDay):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return (
            f"EventDay(id={self._id!r}, event_date={self._event_date!r}, "
            f"operational_profile_id={self._operational_profile_id!r}, "
            f"attendance_level_id={self._attendance_level_id!r}, "
            f"operational_start_min={self._operational_start_min!r}, "
            f"operational_end_min={self._operational_end_min!r})"
        )
