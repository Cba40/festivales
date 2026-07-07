from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.event_day_zone_factor import EventDayZoneFactor
from app.schemas.event_day_zone_factor import EventDayZoneFactorCreate, EventDayZoneFactorUpdate


class EventDayZoneFactorCRUD:
    def create(self, db: Session, obj_in: EventDayZoneFactorCreate) -> EventDayZoneFactor:
        db_obj = EventDayZoneFactor(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, id: str) -> Optional[EventDayZoneFactor]:
        return db.get(EventDayZoneFactor, id)

    def get_by_combo(self, db: Session, event_day_id: str, zone_type_id: str, event_state_id: str) -> Optional[EventDayZoneFactor]:
        stmt = select(EventDayZoneFactor).where(
            and_(
                EventDayZoneFactor.event_day_id == event_day_id,
                EventDayZoneFactor.zone_type_id == zone_type_id,
                EventDayZoneFactor.event_state_id == event_state_id,
            )
        )
        return db.execute(stmt).scalar_one_or_none()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[EventDayZoneFactor]:
        stmt = select(EventDayZoneFactor).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def update(self, db: Session, db_obj: EventDayZoneFactor, obj_in: EventDayZoneFactorUpdate) -> EventDayZoneFactor:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: str) -> EventDayZoneFactor:
        db_obj = db.get(EventDayZoneFactor, id)
        db.delete(db_obj)
        db.commit()
        return db_obj


event_day_zone_factor = EventDayZoneFactorCRUD()
