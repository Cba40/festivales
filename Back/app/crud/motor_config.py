from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.motor_config import RecommendationConfigModel, Stage4ConfigModel, _default_wait_mapping
from app.schemas.motor_config import RecommendationConfigUpdate, Stage4ConfigUpdate
from src.application.context_engine.stage4_config import (
    Stage4Config,
    configure_stage4,
)
from src.application.recommendation.config import (
    RecommendationConfig,
    configure_recommendation,
)

# NOTA: El import directo app/crud/ → src/application/ es un acoplamiento temporal.
# La propagación en memoria (configure_recommendation / configure_stage4) solo
# afecta al worker actual. En despliegues multi-worker se requiere una estrategia
# de sincronización futura (event bus, shared cache, polling desde DB).


async def get_recommendation_config(
    db: AsyncSession,
) -> RecommendationConfigModel:
    result = await db.execute(select(RecommendationConfigModel).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        config = RecommendationConfigModel(id=1)
        db.add(config)
        await db.flush()
        await db.refresh(config)
    return config


async def update_recommendation_config(
    db: AsyncSession,
    obj_in: RecommendationConfigUpdate,
) -> RecommendationConfigModel:
    config = await get_recommendation_config(db)
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    await db.flush()
    await db.refresh(config)

    motor_cfg = RecommendationConfig(
        low_density_saturation_threshold=float(config.low_density_saturation_threshold),
        low_density_reasoning_threshold=float(config.low_density_reasoning_threshold),
        regulated_penalty=float(config.regulated_penalty),
        vip_bonus=float(config.vip_bonus),
        staff_bonus=float(config.staff_bonus),
        mobility_penalty=float(config.mobility_penalty),
    )
    configure_recommendation(motor_cfg)
    return config


async def get_stage4_config(db: AsyncSession) -> Stage4ConfigModel:
    result = await db.execute(select(Stage4ConfigModel).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        config = Stage4ConfigModel(id=1)
        db.add(config)
        await db.flush()
        await db.refresh(config)
    return config


async def update_stage4_config(
    db: AsyncSession,
    obj_in: Stage4ConfigUpdate,
) -> Stage4ConfigModel:
    config = await get_stage4_config(db)
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)
    await db.flush()
    await db.refresh(config)

    raw_mapping = config.wait_time_mapping or _default_wait_mapping()
    mapping = [
        (float(row[0]), float(row[1]), int(row[2]))
        for row in raw_mapping
    ]
    motor_cfg = Stage4Config(
        saturation_high_threshold=float(config.saturation_high_threshold),
        saturation_moderate_threshold=float(config.saturation_moderate_threshold),
        confidence_no_events=float(config.confidence_no_events),
        confidence_planned_events=float(config.confidence_planned_events),
        confidence_incident=float(config.confidence_incident),
        wait_time_mapping=mapping,
    )
    configure_stage4(motor_cfg)
    return config
