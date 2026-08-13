import uuid
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AttendanceLevel(Base):
    __tablename__ = "attendance_levels"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("events.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    min_people: Mapped[int] = mapped_column(Integer, nullable=False)
    max_people: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    event = relationship("Event", back_populates="attendance_levels")

    # Un AttendanceLevel es una estimación NUMÉRICA (min_people -> max_people).
    # El name es solo descriptivo. El catálogo del evento admite niveles con
    # rangos iguales o solapados: no se aplican constraints de unicidad sobre
    # rangos ni nombres. Solo se valida coherencia del rango.
    __table_args__ = (
        CheckConstraint("min_people >= 0", name="chk_attendance_level_min_nonneg"),
        CheckConstraint(
            "max_people IS NULL OR max_people > min_people",
            name="chk_attendance_level_max_gt_min",
        ),
    )