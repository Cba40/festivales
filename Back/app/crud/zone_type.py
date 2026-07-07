from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.zone_type import ZoneType
from app.schemas.zone_type import ZoneTypeCreate, ZoneTypeUpdate


class ZoneTypeCRUD:
    def create(self, db: Session, obj_in: ZoneTypeCreate) -> ZoneType:
        db_obj = ZoneType(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, id: str) -> Optional[ZoneType]:
        return db.get(ZoneType, id)

    def get_by_slug(self, db: Session, slug: str) -> Optional[ZoneType]:
        stmt = select(ZoneType).where(ZoneType.slug == slug)
        return db.execute(stmt).scalar_one_or_none()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[ZoneType]:
        stmt = select(ZoneType).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def update(self, db: Session, db_obj: ZoneType, obj_in: ZoneTypeUpdate) -> ZoneType:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: str) -> ZoneType:
        db_obj = db.get(ZoneType, id)
        db.delete(db_obj)
        db.commit()
        return db_obj


zone_type = ZoneTypeCRUD()
