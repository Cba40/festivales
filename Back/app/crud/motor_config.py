from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.motor_config import RecommendationConfigModel, Stage4ConfigModel
from app.schemas.motor_config import RecommendationConfigUpdate, Stage4ConfigUpdate

# NOTA: El import directo app/crud/ → src/application/ es un acoplamiento temporal.
# La configuración del motor se lee desde la base de datos en cada request
# (src.application.recommendation.config.get_recommendation_config y
# src.application.context_engine.stage4_config.get_stage4_config), por lo que
# no se propaga en memoria al escribir: los workers comparten los mismos valores.


async def get_recommendation_config(
    db: AsyncSession,
) -> RecommendationConfigModel:
    result = await db.execute(select(RecommendationConfigModel).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        config = RecommendationConfigModel(id=1)
        db.add(config)
        await db.flush()
        await db.commit()
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
    await db.commit()
    await db.refresh(config)

    return config


async def get_stage4_config(db: AsyncSession) -> Stage4ConfigModel:
    result = await db.execute(select(Stage4ConfigModel).limit(1))
    config = result.scalar_one_or_none()
    if config is None:
        config = Stage4ConfigModel(id=1)
        db.add(config)
        await db.flush()
        await db.commit()
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
    await db.commit()
    await db.refresh(config)

    return config
