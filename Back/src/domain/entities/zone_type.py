from uuid import UUID, uuid4


class ZoneType:
    def __init__(self, name: str, id: UUID | None = None) -> None:
        resolved_id = id if id is not None else uuid4()
        self._validate(resolved_id, name)
        self._id = resolved_id
        self._name = name.strip()

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @staticmethod
    def _validate(id: UUID, name: str) -> None:
        if not isinstance(id, UUID):
            raise TypeError("id must be a UUID")
        if not name or not name.strip():
            raise ValueError("name must not be empty")
        if len(name) > 50:
            raise ValueError("name must not exceed 50 characters")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ZoneType):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f"ZoneType(id={self._id!r}, name={self._name!r})"
