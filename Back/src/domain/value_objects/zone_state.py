from __future__ import annotations

from uuid import UUID

from src.domain.entities.zone_behavior import FlowRestriction


class ZoneState:
    def __init__(
        self,
        zone_id: UUID,
        operational_state: str,
        availability: int,
        saturation_level: float,
        estimated_wait: int,
        confidence: float,
        reasoning_factors: list[str],
        active_restriction: FlowRestriction,
    ) -> None:
        self._zone_id = zone_id
        self._operational_state = operational_state
        self._availability = availability
        self._saturation_level = saturation_level
        self._estimated_wait = estimated_wait
        self._confidence = confidence
        self._reasoning_factors = list(reasoning_factors)
        self._active_restriction = active_restriction

    @property
    def zone_id(self) -> UUID:
        return self._zone_id

    @property
    def operational_state(self) -> str:
        return self._operational_state

    @property
    def availability(self) -> int:
        return self._availability

    @property
    def saturation_level(self) -> float:
        return self._saturation_level

    @property
    def estimated_wait(self) -> int:
        return self._estimated_wait

    @property
    def confidence(self) -> float:
        return self._confidence

    @property
    def reasoning_factors(self) -> list[str]:
        return list(self._reasoning_factors)

    @property
    def active_restriction(self) -> FlowRestriction:
        return self._active_restriction

    def __repr__(self) -> str:
        return (
            f"ZoneState("
            f"zone_id={self._zone_id!r}, "
            f"operational_state={self._operational_state!r}, "
            f"availability={self._availability!r}, "
            f"saturation_level={self._saturation_level!r}, "
            f"estimated_wait={self._estimated_wait!r}, "
            f"confidence={self._confidence!r}, "
            f"reasoning_factors={self._reasoning_factors!r}, "
            f"active_restriction={self._active_restriction!r})"
        )
