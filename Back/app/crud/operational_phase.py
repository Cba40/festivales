"""CRUD operations for OperationalPhase."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operational_phase import OperationalPhase
from app.models.operational_profile import OperationalProfile
from app.schemas.operational_phase import OperationalPhaseCreate, OperationalPhaseUpdate
from app.services.zone_behavior_sync import sync_zone_behaviors


async def create(db: AsyncSession, obj_in: OperationalPhaseCreate) -> OperationalPhase:
    profile = await db.get(OperationalProfile, obj_in.operational_profile_id)
    if not profile:
        raise ValueError(f"OperationalProfile with id '{obj_in.operational_profile_id}' not found")

    result = await db.execute(
        select(OperationalPhase).where(
            OperationalPhase.operational_profile_id == obj_in.operational_profile_id,
            OperationalPhase.sort_order == obj_in.sort_order,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError(
            f"OperationalPhase with sort_order '{obj_in.sort_order}' "
            f"already exists in profile '{obj_in.operational_profile_id}'"
        )

    db_obj = OperationalPhase(**obj_in.model_dump())
    db.add(db_obj)
    try:
        await db.flush()

        # Integridad P3.1B: sincronizar ZoneBehavior en la misma transacción.
        await db.run_sync(lambda s: sync_zone_behaviors(s, phase_ids=[db_obj.id]))

        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(db_obj)
    return db_obj


async def get_by_id(db: AsyncSession, id: UUID) -> OperationalPhase | None:
    return await db.get(OperationalPhase, id)


async def list_operational_phases(
    db: AsyncSession,
) -> list[OperationalPhase]:
    result = await db.execute(
        select(OperationalPhase).order_by(OperationalPhase.sort_order.asc())
    )
    return list(result.scalars().all())


async def list_by_profile(
    db: AsyncSession, profile_id: UUID,
) -> list[OperationalPhase]:
    result = await db.execute(
        select(OperationalPhase)
        .where(OperationalPhase.operational_profile_id == profile_id)
        .order_by(OperationalPhase.sort_order)
    )
    return list(result.scalars().all())


async def update(
    db: AsyncSession, db_obj: OperationalPhase, obj_in: OperationalPhaseUpdate,
) -> OperationalPhase:
    update_data = obj_in.model_dump(exclude_unset=True)

    if "sort_order" in update_data and update_data["sort_order"] != db_obj.sort_order:
        result = await db.execute(
            select(OperationalPhase).where(
                OperationalPhase.operational_profile_id == db_obj.operational_profile_id,
                OperationalPhase.sort_order == update_data["sort_order"],
            )
        )
        if result.scalar_one_or_none():
            raise ValueError(
                f"OperationalPhase with sort_order '{update_data['sort_order']}' "
                f"already exists in this profile"
            )

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete(db: AsyncSession, id: UUID) -> bool:
    db_obj = await db.get(OperationalPhase, id)
    if not db_obj:
        return False
    await db.delete(db_obj)
    await db.flush()
    await db.commit()
    return True
