from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.event_state import EventState
from app.schemas.event_state import EventStateCreate, EventStateUpdate


class EventStateCRUD:
    def create(self, db: Session, obj_in: EventStateCreate) -> EventState:
        db_obj = EventState(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, id: str) -> Optional[EventState]:
        return db.get(EventState, id)

    def get_by_slug(self, db: Session, slug: str) -> Optional[EventState]:
        stmt = select(EventState).where(EventState.slug == slug)
        return db.execute(stmt).scalar_one_or_none()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[EventState]:
        stmt = select(EventState).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def update(self, db: Session, db_obj: EventState, obj_in: EventStateUpdate) -> EventState:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: str) -> EventState:
        db_obj = db.get(EventState, id)
        db.delete(db_obj)
        db.commit()
        return db_obj


event_state = EventStateCRUD()
