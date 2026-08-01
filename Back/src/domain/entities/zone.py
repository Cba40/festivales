from uuid import UUID, uuid4


class Zone:
    def __init__(
        self,
        name: str,
        zone_type_id: UUID,
        capacity: int,
        id: UUID | None = None,
        type: str = "",
        subtipo: str | None = None,
    ) -> None:
        resolved_id = id if id is not None else uuid4()
        self._validate(resolved_id, name, zone_type_id, capacity, type, subtipo)
        self._id = resolved_id
        self._name = name.strip()
        self._zone_type_id = zone_type_id
        self._capacity = capacity
        self._type = type
        self._subtipo = subtipo

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def zone_type_id(self) -> UUID:
        return self._zone_type_id

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def type(self) -> str:
        return self._type

    @property
    def subtipo(self) -> str | None:
        return self._subtipo

    @staticmethod
    def _validate(
        id: UUID,
        name: str,
        zone_type_id: UUID,
        capacity: int,
        type: str,
        subtipo: str | None,
    ) -> None:
        if not isinstance(id, UUID):
            raise TypeError("id must be a UUID")
        if not name or not name.strip():
            raise ValueError("name must not be empty")
        if len(name) > 100:
            raise ValueError("name must not exceed 100 characters")
        if not isinstance(zone_type_id, UUID):
            raise TypeError("zone_type_id must be a UUID")
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        if not isinstance(type, str):
            raise TypeError("type must be a string")
        if subtipo is not None and not isinstance(subtipo, str):
            raise TypeError("subtipo must be a string or None")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Zone):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return (
            f"Zone(id={self._id!r}, name={self._name!r}, "
            f"zone_type_id={self._zone_type_id!r}, capacity={self._capacity!r}, "
            f"type={self._type!r}, subtipo={self._subtipo!r})"
        )
