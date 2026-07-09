from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attendance_level import AttendanceLevel
from app.schemas.attendance_level import AttendanceLevelCreate, AttendanceLevelUpdate


class AttendanceLevelCRUD:

    def _validate_ranges(self, db: Session, event_id: str, new_min: int, new_max: Optional[int], exclude_id: Optional[str] = None) -> None:
        stmt = select(AttendanceLevel).where(AttendanceLevel.event_id == event_id)
        if exclude_id:
            stmt = stmt.where(AttendanceLevel.id != exclude_id)
        existing = list(db.execute(stmt).scalars().all())

        ranges = [(al.min_people, al.max_people) for al in existing]
        ranges.append((new_min, new_max))
        ranges.sort(key=lambda x: x[0])

        for i in range(len(ranges) - 1):
            curr_max = ranges[i][1]
            next_min = ranges[i + 1][0]
            if curr_max is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Solo el último rango puede tener max_people = NULL",
                )
            if curr_max >= next_min:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Rangos solapados: max_people={curr_max} >= min_people={next_min}",
                )
            if curr_max + 1 != next_min:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Hay un hueco entre rangos: max_people={curr_max} → min_people={next_min}",
                )

    def create(self, db: Session, obj_in: AttendanceLevelCreate, event_id: str) -> AttendanceLevel:
        self._validate_ranges(db, event_id, obj_in.min_people, obj_in.max_people)
        db_obj = AttendanceLevel(event_id=event_id, **obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, id: str) -> Optional[AttendanceLevel]:
        return db.get(AttendanceLevel, id)

    def get_by_event(self, db: Session, event_id: str) -> list[AttendanceLevel]:
        stmt = select(AttendanceLevel).where(AttendanceLevel.event_id == event_id).order_by(AttendanceLevel.min_people)
        return list(db.execute(stmt).scalars().all())

    def update(self, db: Session, db_obj: AttendanceLevel, obj_in: AttendanceLevelUpdate) -> AttendanceLevel:
        update_data = obj_in.model_dump(exclude_unset=True)
        if 'min_people' in update_data or 'max_people' in update_data:
            new_min = update_data.get('min_people', db_obj.min_people)
            new_max = update_data.get('max_people', db_obj.max_people)
            self._validate_ranges(db, db_obj.event_id, new_min, new_max, exclude_id=db_obj.id)
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
