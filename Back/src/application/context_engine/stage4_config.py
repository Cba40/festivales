from __future__ import annotations


_STAGE4_CONFIG: Stage4Config | None = None


class Stage4Config:
    def __init__(
        self,
        saturation_high_threshold: float = 0.9,
        saturation_moderate_threshold: float = 0.5,
    ) -> None:
        self._saturation_high_threshold = saturation_high_threshold
        self._saturation_moderate_threshold = saturation_moderate_threshold

    @property
    def saturation_high_threshold(self) -> float:
        return self._saturation_high_threshold

    @property
    def saturation_moderate_threshold(self) -> float:
        return self._saturation_moderate_threshold


def get_stage4_config() -> Stage4Config:
    global _STAGE4_CONFIG
    if _STAGE4_CONFIG is None:
        _STAGE4_CONFIG = Stage4Config()
    return _STAGE4_CONFIG


def configure_stage4(config: Stage4Config) -> None:
    global _STAGE4_CONFIG
    _STAGE4_CONFIG = config
