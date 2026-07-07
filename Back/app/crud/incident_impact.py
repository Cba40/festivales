from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.incident_impact import IncidentImpact
from app.schemas.incident_impact import IncidentImpactCreate, IncidentImpactUpdate


class IncidentImpactCRUD:
    def create(self, db: Session, obj_in: IncidentImpactCreate) -> IncidentImpact:
        db_obj = IncidentImpact(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, id: str) -> Optional[IncidentImpact]:
        return db.get(IncidentImpact, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> list[IncidentImpact]:
        stmt = select(IncidentImpact).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars().all())

    def update(self, db: Session, db_obj: IncidentImpact, obj_in: IncidentImpactUpdate) -> IncidentImpact:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: str) -> IncidentImpact:
        db_obj = db.get(IncidentImpact, id)
        db.delete(db_obj)
        db.commit()
        return db_obj


incident_impact = IncidentImpactCRUD()
