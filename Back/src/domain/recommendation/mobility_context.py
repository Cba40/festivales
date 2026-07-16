from __future__ import annotations

from uuid import UUID


class MobilityContext:
    def __init__(
        self,
        current_zone_id: UUID | None,
        speed: float,
        accessibility_required: bool,
    ) -> None:
        self._current_zone_id = current_zone_id
        self._speed = speed
        self._accessibility_required = accessibility_required

    @property
    def current_zone_id(self) -> UUID | None:
        return self._current_zone_id

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def accessibility_required(self) -> bool:
        return self._accessibility_required

    def __repr__(self) -> str:
        return (
            f"MobilityContext("
            f"current_zone_id={self._current_zone_id!r}, "
            f"speed={self._speed!r}, "
            f"accessibility_required={self._accessibility_required!r})"
        )
