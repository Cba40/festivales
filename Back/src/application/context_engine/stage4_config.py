from __future__ import annotations

from collections.abc import Mapping


_STAGE4_CONFIG: Stage4Config | None = None


def _default_wait_mapping() -> list[tuple[float, float, int]]:
    return [
        (0.0, 0.3, 0),
        (0.3, 0.5, 5),
        (0.5, 0.7, 10),
        (0.7, 0.9, 15),
        (0.9, 1.01, 20),
    ]


class Stage4Config:
    def __init__(
        self,
        saturation_high_threshold: float = 0.9,
        saturation_moderate_threshold: float = 0.5,
        confidence_no_events: float = 1.0,
        confidence_planned_events: float = 0.8,
        confidence_incident: float = 0.5,
        wait_time_mapping: list[tuple[float, float, int]] | None = None,
    ) -> None:
        self._saturation_high_threshold = saturation_high_threshold
        self._saturation_moderate_threshold = saturation_moderate_threshold
        self._confidence_no_events = confidence_no_events
        self._confidence_planned_events = confidence_planned_events
        self._confidence_incident = confidence_incident
        self._wait_time_mapping = (
            wait_time_mapping if wait_time_mapping is not None else _default_wait_mapping()
        )

    @property
    def saturation_high_threshold(self) -> float:
        return self._saturation_high_threshold

    @property
    def saturation_moderate_threshold(self) -> float:
        return self._saturation_moderate_threshold

    @property
    def confidence_no_events(self) -> float:
        return self._confidence_no_events

    @property
    def confidence_planned_events(self) -> float:
        return self._confidence_planned_events

    @property
    def confidence_incident(self) -> float:
        return self._confidence_incident

    @property
    def wait_time_mapping(self) -> list[tuple[float, float, int]]:
        return list(self._wait_time_mapping)


def get_stage4_config() -> Stage4Config:
    global _STAGE4_CONFIG
    if _STAGE4_CONFIG is None:
        _STAGE4_CONFIG = Stage4Config()
    return _STAGE4_CONFIG


def configure_stage4(config: Stage4Config) -> None:
    global _STAGE4_CONFIG
    _STAGE4_CONFIG = config
