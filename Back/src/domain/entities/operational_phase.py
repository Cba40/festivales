from uuid import UUID, uuid4


class OperationalPhase:
    def __init__(self, name: str, sequence_order: int, id: UUID | None = None) -> None:
        resolved_id = id if id is not None else uuid4()
        self._validate(resolved_id, name, sequence_order)
        self._id = resolved_id
        self._name = name.strip()
        self._sequence_order = sequence_order

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def sequence_order(self) -> int:
        return self._sequence_order

    @staticmethod
    def _validate(id: UUID, name: str, sequence_order: int) -> None:
        if not isinstance(id, UUID):
            raise TypeError("id must be a UUID")
        if not name or not name.strip():
            raise ValueError("name must not be empty")
        if len(name) > 50:
            raise ValueError("name must not exceed 50 characters")
        if isinstance(sequence_order, bool) or not isinstance(sequence_order, int) or sequence_order <= 0:
            raise ValueError("sequence_order must be a positive integer")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OperationalPhase):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return (
            f"OperationalPhase(id={self._id!r}, name={self._name!r}, "
            f"sequence_order={self._sequence_order!r})"
        )
