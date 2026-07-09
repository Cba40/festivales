from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.state_override import StateOverride
from app.schemas.state_override import StateOverrideCreate, StateOverrideUpdate


class StateOverrideCRUD:
    def create(self, db: Session, obj_in: StateOverrideCreate) -> StateOverride:
        db_obj = StateOverride(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, id: str) -> Optional[StateOverride]:
        return db.get(StateOverride, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[StateOverride]:
        stmt = select(StateOverride).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def get_active_overrides(self, db: Session, event_day_id: str, current_min: int) -> list[StateOverride]:
        stmt = select(StateOverride).where(
            and_(
                StateOverride.event_day_id == event_day_id,
                StateOverride.is_active == True,
                StateOverride.start_min <= current_min,
                StateOverride.end_min > current_min,
            )
        )
        return list(db.execute(stmt).scalars().all())

    def update(self, db: Session, db_obj: StateOverride, obj_in: StateOverrideUpdate) -> StateOverride:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: str) -> StateOverride:
        db_obj = db.get(StateOverride, id)
        db.delete(db_obj)
        db.commit()
        return db_obj


state_override = StateOverrideCRUD()
