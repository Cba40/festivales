from uuid import UUID, uuid4


class AttendanceLevel:
    """Nivel de concurrencia estimada para una jornada.

    RFC-007 / Sprint P7: AttendanceLevel representa únicamente la concurrencia
    estimada del día (rango de personas). La intensidad operativa ya no es
    global: pertenece a cada EventDayPhase (campo intensity).
    """

    def __init__(
        self,
        name: str,
        min_people: int,
        max_people: int | None = None,
        event_day_id: UUID | None = None,
        id: UUID | None = None,
    ) -> None:
        resolved_id = id if id is not None else uuid4()
        self._validate(resolved_id, name, min_people, max_people)
        self._id = resolved_id
        self._name = name.strip()
        self._min_people = min_people
        self._max_people = max_people
        self._event_day_id = event_day_id

    @property
    def event_day_id(self) -> UUID | None:
        return self._event_day_id

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def min_people(self) -> int:
        return self._min_people

    @property
    def max_people(self) -> int | None:
        return self._max_people

    @staticmethod
    def _validate(
        id: UUID,
        name: str,
        min_people: int,
        max_people: int | None,
    ) -> None:
        if not isinstance(id, UUID):
            raise TypeError("id must be a UUID")
        if not name or not name.strip():
            raise ValueError("name must not be empty")
        if len(name) > 50:
            raise ValueError("name must not exceed 50 characters")
        if isinstance(min_people, bool) or not isinstance(min_people, int):
            raise TypeError("min_people must be an integer")
        if min_people < 0:
            raise ValueError("min_people must be >= 0")
        if max_people is not None:
            if isinstance(max_people, bool) or not isinstance(max_people, int):
                raise TypeError("max_people must be an integer or None")
            if max_people <= min_people:
                raise ValueError("max_people must be greater than min_people")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AttendanceLevel):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return (
            f"AttendanceLevel(id={self._id!r}, name={self._name!r}, "
            f"min_people={self._min_people!r}, max_people={self._max_people!r}, "
            f"event_day_id={self._event_day_id!r})"
        )