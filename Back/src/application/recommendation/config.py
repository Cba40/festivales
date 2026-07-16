from __future__ import annotations

_RECOMMENDATION_CONFIG: RecommendationConfig | None = None


class RecommendationConfig:
    def __init__(
        self,
        low_density_saturation_threshold: float = 0.5,
        low_density_reasoning_threshold: float = 0.3,
        regulated_penalty: float = 0.3,
        vip_bonus: float = 0.1,
        staff_bonus: float = 0.2,
        mobility_penalty: float = 0.15,
    ) -> None:
        self._low_density_saturation_threshold = low_density_saturation_threshold
        self._low_density_reasoning_threshold = low_density_reasoning_threshold
        self._regulated_penalty = regulated_penalty
        self._vip_bonus = vip_bonus
        self._staff_bonus = staff_bonus
        self._mobility_penalty = mobility_penalty

    @property
    def low_density_saturation_threshold(self) -> float:
        return self._low_density_saturation_threshold

    @property
    def low_density_reasoning_threshold(self) -> float:
        return self._low_density_reasoning_threshold

    @property
    def regulated_penalty(self) -> float:
        return self._regulated_penalty

    @property
    def vip_bonus(self) -> float:
        return self._vip_bonus

    @property
    def staff_bonus(self) -> float:
        return self._staff_bonus

    @property
    def mobility_penalty(self) -> float:
        return self._mobility_penalty


def get_recommendation_config() -> RecommendationConfig:
    global _RECOMMENDATION_CONFIG
    if _RECOMMENDATION_CONFIG is None:
        _RECOMMENDATION_CONFIG = RecommendationConfig()
    return _RECOMMENDATION_CONFIG


def configure_recommendation(config: RecommendationConfig) -> None:
    global _RECOMMENDATION_CONFIG
    _RECOMMENDATION_CONFIG = config
