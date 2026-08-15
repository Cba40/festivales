from __future__ import annotations

from uuid import UUID


class MobilityContext:
    def __init__(
        self,
        current_zone_id: UUID | None,
        speed: float,
        accessibility_required: bool,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> None:
        self._current_zone_id = current_zone_id
        self._speed = speed
        self._accessibility_required = accessibility_required
        self._latitude = latitude
        self._longitude = longitude

        if latitude is not None and not (-90.0 <= latitude <= 90.0):
            raise ValueError(f"Latitude must be between -90 and 90, got {latitude}")
        if longitude is not None and not (-180.0 <= longitude <= 180.0):
            raise ValueError(f"Longitude must be between -180 and 180, got {longitude}")

    @property
    def current_zone_id(self) -> UUID | None:
        return self._current_zone_id

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def accessibility_required(self) -> bool:
        return self._accessibility_required

    @property
    def latitude(self) -> float | None:
        return self._latitude

    @property
    def longitude(self) -> float | None:
        return self._longitude

    def __repr__(self) -> str:
        return (
            f"MobilityContext("
            f"current_zone_id={self._current_zone_id!r}, "
            f"speed={self._speed!r}, "
            f"accessibility_required={self._accessibility_required!r}, "
            f"latitude={self._latitude!r}, "
            f"longitude={self._longitude!r})"
        )
