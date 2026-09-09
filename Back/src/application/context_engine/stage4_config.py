from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


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


async def get_stage4_config(db: AsyncSession) -> Stage4Config:
    """Lee la configuración de Stage 4 desde la base de datos.

    Consulta directa a `stage4_config` en cada request para garantizar
    consistencia entre workers (sin singleton en memoria).
    Si no existe registro, devuelve la instancia por defecto.
    """
    from app.models.motor_config import Stage4ConfigModel

    result = await db.execute(select(Stage4ConfigModel).limit(1))
    row = result.scalar_one_or_none()
    if row is None:
        return Stage4Config()
    return Stage4Config(
        saturation_high_threshold=float(row.saturation_high_threshold),
        saturation_moderate_threshold=float(row.saturation_moderate_threshold),
    )
