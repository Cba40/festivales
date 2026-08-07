from __future__ import annotations

from src.domain.entities.attendance_level import AttendanceLevel
from src.infrastructure.persistence.models.attendance_level import (
    AttendanceLevelModel,
)


def attendance_level_to_domain(model: AttendanceLevelModel) -> AttendanceLevel:
    return AttendanceLevel(
        id=model.id,
        name=model.name,
        min_people=model.min_people,
        max_people=model.max_people,
    )


def attendance_level_to_model(entity: AttendanceLevel) -> AttendanceLevelModel:
    return AttendanceLevelModel(
        id=entity.id,
        name=entity.name,
        min_people=entity.min_people,
        max_people=entity.max_people,
    )