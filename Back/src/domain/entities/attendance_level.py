from uuid import UUID, uuid4


class AttendanceLevel:
    def __init__(self, name: str, multiplier: float, id: UUID | None = None) -> None:
        resolved_id = id if id is not None else uuid4()
        self._validate(resolved_id, name, multiplier)
        self._id = resolved_id
        self._name = name.strip()
        self._multiplier = multiplier

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def multiplier(self) -> float:
        return self._multiplier

    @staticmethod
    def _validate(id: UUID, name: str, multiplier: float) -> None:
        if not isinstance(id, UUID):
            raise TypeError("id must be a UUID")
        if not name or not name.strip():
            raise ValueError("name must not be empty")
        if len(name) > 50:
            raise ValueError("name must not exceed 50 characters")
        if isinstance(multiplier, bool) or not isinstance(multiplier, (int, float)):
            raise TypeError("multiplier must be a number")
        if multiplier < 0.1 or multiplier > 2.0:
            raise ValueError("multiplier must be between 0.1 and 2.0")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AttendanceLevel):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return (
            f"AttendanceLevel(id={self._id!r}, name={self._name!r}, "
            f"multiplier={self._multiplier!r})"
        )
