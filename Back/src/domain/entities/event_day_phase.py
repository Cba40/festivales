from uuid import UUID, uuid4


class EventDayPhase:
    def __init__(
        self,
        event_day_id: UUID,
        operational_phase_id: UUID,
        start_min: int,
        end_min: int,
        id: UUID | None = None,
    ) -> None:
        resolved_id = id if id is not None else uuid4()
        self._validate(resolved_id, event_day_id, operational_phase_id, start_min, end_min)
        self._id = resolved_id
        self._event_day_id = event_day_id
        self._operational_phase_id = operational_phase_id
        self._start_min = start_min
        self._end_min = end_min

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def event_day_id(self) -> UUID:
        return self._event_day_id

    @property
    def operational_phase_id(self) -> UUID:
        return self._operational_phase_id

    @property
    def start_min(self) -> int:
        return self._start_min

    @property
    def end_min(self) -> int:
        return self._end_min

    @staticmethod
    def _validate(
        id: UUID,
        event_day_id: UUID,
        operational_phase_id: UUID,
        start_min: int,
        end_min: int,
    ) -> None:
        if not isinstance(id, UUID):
            raise TypeError("id must be a UUID")
        if not isinstance(event_day_id, UUID):
            raise TypeError("event_day_id must be a UUID")
        if not isinstance(operational_phase_id, UUID):
            raise TypeError("operational_phase_id must be a UUID")
        if isinstance(start_min, bool) or not isinstance(start_min, int):
            raise TypeError("start_min must be an integer")
        if start_min < 0:
            raise ValueError("start_min must be >= 0")
        if isinstance(end_min, bool) or not isinstance(end_min, int):
            raise TypeError("end_min must be an integer")
        if end_min <= start_min:
            raise ValueError("end_min must be greater than start_min")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EventDayPhase):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return (
            f"EventDayPhase(id={self._id!r}, event_day_id={self._event_day_id!r}, "
            f"operational_phase_id={self._operational_phase_id!r}, "
            f"start_min={self._start_min!r}, end_min={self._end_min!r})"
        )
