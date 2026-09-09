from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class RecommendationConfig:
    def __init__(
        self,
        low_density_saturation_threshold: float = 0.5,
        low_density_reasoning_threshold: float = 0.3,
        regulated_penalty: float = 0.3,
        vip_bonus: float = 0.1,
        staff_bonus: float = 0.2,
        mobility_penalty: float = 0.15,
        min_availability_threshold: float = 0.05,
    ) -> None:
        self._low_density_saturation_threshold = low_density_saturation_threshold
        self._low_density_reasoning_threshold = low_density_reasoning_threshold
        self._regulated_penalty = regulated_penalty
        self._vip_bonus = vip_bonus
        self._staff_bonus = staff_bonus
        self._mobility_penalty = mobility_penalty
        self._min_availability_threshold = min_availability_threshold

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

    @property
    def min_availability_threshold(self) -> float:
        return self._min_availability_threshold


async def get_recommendation_config(db: AsyncSession) -> RecommendationConfig:
    """Lee la configuración de recomendaciones desde la base de datos.

    Consulta directa a `recommendation_config` en cada request para
    garantizar consistencia entre workers (sin singleton en memoria).
    Si no existe registro, devuelve la instancia por defecto.
    """
    from app.models.motor_config import RecommendationConfigModel

    result = await db.execute(select(RecommendationConfigModel).limit(1))
    row = result.scalar_one_or_none()
    if row is None:
        return RecommendationConfig()
    return RecommendationConfig(
        low_density_saturation_threshold=float(row.low_density_saturation_threshold),
        low_density_reasoning_threshold=float(row.low_density_reasoning_threshold),
        regulated_penalty=float(row.regulated_penalty),
        vip_bonus=float(row.vip_bonus),
        staff_bonus=float(row.staff_bonus),
        mobility_penalty=float(row.mobility_penalty),
    )
