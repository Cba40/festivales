from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from src.domain.entities.zone_behavior import FlowRestriction


class ZoneState:
    def __init__(
        self,
        zone_id: UUID,
        operational_state: str,
        availability: int | None = None,
        saturation_level: float | None = None,
        estimated_wait: int | None = None,
        confidence: float | None = None,
        reasoning_factors: list[str] | None = None,
        active_restriction: FlowRestriction | None = None,
        type: str = "",
        subtipo: str | None = None,
        projected_density: int = 0,
        model_result: Mapping[str, object] | None = None,
    ) -> None:
        self._zone_id = zone_id
        self._operational_state = operational_state
        self._availability = availability
        self._saturation_level = saturation_level
        self._estimated_wait = estimated_wait
        self._confidence = confidence
        self._reasoning_factors = list(reasoning_factors or [])
        self._active_restriction = active_restriction
        self._type = type
        self._subtipo = subtipo
        self._projected_density = projected_density
        self._model_result = dict(model_result) if model_result is not None else None

    @property
    def zone_id(self) -> UUID:
        return self._zone_id

    @property
    def operational_state(self) -> str:
        return self._operational_state

    @property
    def availability(self) -> int | None:
        return self._availability

    @property
    def saturation_level(self) -> float | None:
        return self._saturation_level

    @property
    def estimated_wait(self) -> int | None:
        return self._estimated_wait

    @property
    def confidence(self) -> float | None:
        return self._confidence

    @property
    def reasoning_factors(self) -> list[str]:
        return list(self._reasoning_factors)

    @property
    def active_restriction(self) -> FlowRestriction | None:
        return self._active_restriction

    @property
    def type(self) -> str:
        return self._type

    @property
    def subtipo(self) -> str | None:
        return self._subtipo

    @property
    def projected_density(self) -> int:
        return self._projected_density

    @property
    def model_result(self) -> Mapping[str, object] | None:
        return dict(self._model_result) if self._model_result is not None else None

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
            f"active_restriction={self._active_restriction!r}, "
            f"type={self._type!r}, subtipo={self._subtipo!r}, "
            f"projected_density={self._projected_density!r}, "
            f"model_result={self._model_result!r})"
        )