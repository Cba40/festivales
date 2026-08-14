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
        latitude: float | None = None,
        longitude: float | None = None,
        reference_point_distance: float | None = None,
        available_capacity: int | None = None,
    ) -> None:
        resolved_id = id if id is not None else uuid4()
        self._validate(
            resolved_id,
            name,
            zone_type_id,
            capacity,
            type,
            subtipo,
            latitude,
            longitude,
            reference_point_distance,
            available_capacity,
        )
        self._id = resolved_id
        self._name = name.strip()
        self._zone_type_id = zone_type_id
        self._capacity = capacity
        self._type = type
        self._subtipo = subtipo
        self._latitude = latitude
        self._longitude = longitude
        self._reference_point_distance = reference_point_distance
        self._available_capacity = available_capacity

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

    @property
    def latitude(self) -> float | None:
        return self._latitude

    @property
    def longitude(self) -> float | None:
        return self._longitude

    @property
    def reference_point_distance(self) -> float | None:
        return self._reference_point_distance

    @property
    def available_capacity(self) -> int | None:
        return self._available_capacity

    @staticmethod
    def _validate(
        id: UUID,
        name: str,
        zone_type_id: UUID,
        capacity: int,
        type: str,
        subtipo: str | None,
        latitude: float | None = None,
        longitude: float | None = None,
        reference_point_distance: float | None = None,
        available_capacity: int | None = None,
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
        if latitude is not None:
            if isinstance(latitude, bool) or not isinstance(latitude, float):
                raise TypeError("latitude must be a float or None")
            if not -90.0 <= latitude <= 90.0:
                raise ValueError("latitude must be within [-90, 90]")
        if longitude is not None:
            if isinstance(longitude, bool) or not isinstance(longitude, float):
                raise TypeError("longitude must be a float or None")
            if not -180.0 <= longitude <= 180.0:
                raise ValueError("longitude must be within [-180, 180]")
        if reference_point_distance is not None:
            if (
                isinstance(reference_point_distance, bool)
                or not isinstance(reference_point_distance, float)
            ):
                raise TypeError("reference_point_distance must be a float or None")
            if reference_point_distance < 0.0:
                raise ValueError("reference_point_distance must be non-negative")
        if available_capacity is not None:
            if (
                isinstance(available_capacity, bool)
                or not isinstance(available_capacity, int)
            ):
                raise TypeError("available_capacity must be an integer or None")
            if available_capacity < 0:
                raise ValueError("available_capacity must be non-negative")

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
            f"type={self._type!r}, subtipo={self._subtipo!r}, "
            f"latitude={self._latitude!r}, longitude={self._longitude!r}, "
            f"reference_point_distance={self._reference_point_distance!r}, "
            f"available_capacity={self._available_capacity!r})"
        )
