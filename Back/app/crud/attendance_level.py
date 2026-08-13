from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.attendance_level import AttendanceLevel
from app.schemas.attendance_level import AttendanceLevelCreate, AttendanceLevelUpdate


class AttendanceLevelCRUD:

    def _validate_ranges(self, db: Session, event_id: str, new_min: int, new_max: Optional[int], exclude_id: Optional[str] = None) -> None:
        """Validar coherencia básica del rango.

        NO valida solapamientos ni rangos consecutivos: el catálogo del evento
        admite niveles con rangos iguales o solapados. Única regla de negocio:
        min_people >= 0 y max_people > min_people (o NULL = sin límite).
        """
        if new_min < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"min_people={new_min} debe ser mayor o igual a 0",
            )
        if new_max is not None and new_max <= new_min:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"max_people={new_max} debe ser mayor que min_people={new_min}",
            )
        # Permitir solapamientos y rangos iguales entre niveles del mismo evento.
        # Dos jornadas pueden seleccionar el mismo nivel, o niveles con los mismos
        # rangos o rangos solapados.

    def create(self, db: Session, obj_in: AttendanceLevelCreate, event_id: str) -> AttendanceLevel:
        self._validate_ranges(db, event_id, obj_in.min_people, obj_in.max_people)
        db_obj = AttendanceLevel(
            event_id=event_id,
            name=obj_in.name,
            min_people=obj_in.min_people,
            max_people=obj_in.max_people,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get(self, db: Session, id: str) -> Optional[AttendanceLevel]:
        return db.get(AttendanceLevel, id)

    def get_by_event(self, db: Session, event_id: str) -> list[AttendanceLevel]:
        stmt = select(AttendanceLevel).where(AttendanceLevel.event_id == event_id).order_by(AttendanceLevel.min_people)
        return list(db.execute(stmt).scalars().all())

    def update(self, db: Session, db_obj: AttendanceLevel, obj_in: AttendanceLevelUpdate, event_id: Optional[str] = None) -> AttendanceLevel:
        update_data = obj_in.model_dump(exclude_unset=True)
        if 'min_people' in update_data or 'max_people' in update_data:
            new_min = update_data.get('min_people', db_obj.min_people)
            new_max = update_data.get('max_people', db_obj.max_people)
            scope = event_id if event_id is not None else db_obj.event_id
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
        try:
            db.delete(db_obj)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El nivel de asistencia está en uso por una o más jornadas y no puede eliminarse",
            )
        return db_obj


attendance_level = AttendanceLevelCRUD()