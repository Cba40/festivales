"""CRUD operations for ZoneBehavior."""
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.zone_behavior import ZoneBehavior
from app.models.operational_phase import OperationalPhase
from app.models.zone_type import ZoneType
from app.schemas.zone_behavior import ZoneBehaviorCreate, ZoneBehaviorUpdate

# Valores por defecto coherentes con los defaults del modelo y del schema
# (flujo "OPEN", densidad 0.5 y factores neutros 1.0, como en §11 / seeds).
DEFAULT_SATURATION_FACTOR = Decimal("1.0")
DEFAULT_AVAILABILITY_FACTOR = Decimal("1.0")
DEFAULT_RESOURCE_FACTOR = Decimal("1.0")
DEFAULT_PRIORITY_WEIGHT = Decimal("1.0")
DEFAULT_DENSITY_FACTOR = 0.5
DEFAULT_FLOW_RESTRICTION = "OPEN"


def default_behavior(phase_id: UUID, zone_type_id: str) -> ZoneBehavior:
    """Construye un ZoneBehavior con valores por defecto para (phase, zone_type)."""
    return ZoneBehavior(
        operational_phase_id=phase_id,
        zone_type_id=zone_type_id,
        saturation_factor=DEFAULT_SATURATION_FACTOR,
        availability_factor=DEFAULT_AVAILABILITY_FACTOR,
        resource_factor=DEFAULT_RESOURCE_FACTOR,
        priority_weight=DEFAULT_PRIORITY_WEIGHT,
        density_factor=DEFAULT_DENSITY_FACTOR,
        flow_restriction=DEFAULT_FLOW_RESTRICTION,
    )


async def create(db: AsyncSession, obj_in: ZoneBehaviorCreate) -> ZoneBehavior:
    phase = await db.get(OperationalPhase, obj_in.operational_phase_id)
    if not phase:
        raise ValueError(f"OperationalPhase with id '{obj_in.operational_phase_id}' not found")

    zone_type = await db.get(ZoneType, obj_in.zone_type_id)
    if not zone_type:
        raise ValueError(f"ZoneType with id '{obj_in.zone_type_id}' not found")

    result = await db.execute(
        select(ZoneBehavior).where(
            ZoneBehavior.operational_phase_id == obj_in.operational_phase_id,
            ZoneBehavior.zone_type_id == obj_in.zone_type_id,
        )
    )
    if result.scalar_one_or_none():
        raise ValueError(
            f"ZoneBehavior already exists for phase '{obj_in.operational_phase_id}' "
            f"and zone type '{obj_in.zone_type_id}'"
        )

    db_obj = ZoneBehavior(**obj_in.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get_by_id(db: AsyncSession, id: UUID) -> ZoneBehavior | None:
    return await db.get(ZoneBehavior, id)


async def list_by_phase(
    db: AsyncSession, phase_id: UUID,
) -> list[ZoneBehavior]:
    result = await db.execute(
        select(ZoneBehavior).where(ZoneBehavior.operational_phase_id == phase_id)
    )
    return list(result.scalars().all())


async def update(
    db: AsyncSession, db_obj: ZoneBehavior, obj_in: ZoneBehaviorUpdate,
) -> ZoneBehavior:
    update_data = obj_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(db_obj, field, value)

    await db.flush()
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete(db: AsyncSession, id: UUID) -> bool:
    db_obj = await db.get(ZoneBehavior, id)
    if not db_obj:
        return False
    await db.delete(db_obj)
    await db.flush()
    await db.commit()
    return True
