from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attendance_level import AttendanceLevel
from app.schemas.attendance_level import AttendanceLevelCreate, AttendanceLevelUpdate


class AttendanceLevelCRUD:

    def _validate_ranges(self, db: Session, event_day_id: str, new_min: int, new_max: Optional[int], exclude_id: Optional[str] = None) -> None:
        if new_min is not None and new_max is not None and new_max < new_min:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"min_people={new_min} no puede ser mayor que max_people={new_max}",
            )

        stmt = select(AttendanceLevel).where(AttendanceLevel.event_day_id == event_day_id)
        if exclude_id:
            stmt = stmt.where(AttendanceLevel.id != exclude_id)
        existing = list(db.execute(stmt).scalars().all())

        new_hi = new_max if new_max is not None else float("inf")

        for al in existing:
            lo = al.min_people
            hi = al.max_people if al.max_people is not None else float("inf")
            overlaps = lo <= new_hi and hi >= new_min
            if overlaps:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Rangos solapados",
                )

    def create(self, db: Session, obj_in: AttendanceLevelCreate, event_day_id: str) -> AttendanceLevel:
        self._validate_ranges(db, event_day_id, obj_in.min_people, obj_in.max_people)
        db_obj = AttendanceLevel(event_day_id=event_day_id, name=obj_in.name, min_people=obj_in.min_people, max_people=obj_in.max_people)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, id: str) -> Optional[AttendanceLevel]:
        return db.get(AttendanceLevel, id)

    def get_by_event_day(self, db: Session, event_day_id: str) -> list[AttendanceLevel]:
        stmt = select(AttendanceLevel).where(AttendanceLevel.event_day_id == event_day_id).order_by(AttendanceLevel.min_people)
        return list(db.execute(stmt).scalars().all())

    def update(self, db: Session, db_obj: AttendanceLevel, obj_in: AttendanceLevelUpdate, event_day_id: Optional[str] = None) -> AttendanceLevel:
        update_data = obj_in.model_dump(exclude_unset=True)
        if 'min_people' in update_data or 'max_people' in update_data:
            new_min = update_data.get('min_people', db_obj.min_people)
            new_max = update_data.get('max_people', db_obj.max_people)
            scope = event_day_id if event_day_id is not None else db_obj.event_day_id
            self._validate_ranges(db, scope, new_min, new_max, exclude_id=db_obj.id)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: str) -> AttendanceLevel:
        db_obj = db.get(AttendanceLevel, id)
        if not db_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attendance level not found")
        db.delete(db_obj)
        db.commit()
        return db_obj


attendance_level = AttendanceLevelCRUD()