from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from src.domain.entities.event_day_phase import EventDayPhase

if TYPE_CHECKING:
    from src.domain.entities.attendance_level import AttendanceLevel


class EventDay:
    """Concentra la configuracion operacional de una jornada.

    RFC-007: EventDay agrupa fecha, horario operativo, la coleccion de
    AttendanceLevel del día y las fases (EventDayPhase). La evolucion temporal
    del evento pertenece a las fases. OperationalProfile queda deprecado como
    entidad de compatibilidad.
    """

    def __init__(
        self,
        event_date: date,
        operational_profile_id: UUID | None,
        operational_start_min: int,
        operational_end_min: int,
        phases: tuple[EventDayPhase, ...],
        attendance_levels: tuple["AttendanceLevel", ...] = (),
        id: UUID | None = None,
    ) -> None:
        resolved_id = id if id is not None else uuid4()
        self._validate(
            resolved_id,
            event_date,
            operational_profile_id,
            operational_start_min,
            operational_end_min,
            phases,
        )
        self._id = resolved_id
        self._event_date = event_date
        self._operational_profile_id = operational_profile_id
        self._operational_start_min = operational_start_min
        self._operational_end_min = operational_end_min
        self._phases = phases
        self._attendance_levels = attendance_levels

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def event_date(self) -> date:
        return self._event_date

    @property
    def operational_profile_id(self) -> UUID | None:
        return self._operational_profile_id

    @property
    def operational_start_min(self) -> int:
        return self._operational_start_min

    @property
    def operational_end_min(self) -> int:
        return self._operational_end_min

    @property
    def phases(self) -> tuple["EventDayPhase", ...]:
        return self._phases

    @property
    def attendance_levels(self) -> tuple["AttendanceLevel", ...]:
        return self._attendance_levels

    @staticmethod
    def _validate(
        id: UUID,
        event_date: date,
        operational_profile_id: UUID,
        operational_start_min: int,
        operational_end_min: int,
        phases: tuple["EventDayPhase", ...],
    ) -> None:
        if not isinstance(id, UUID):
            raise TypeError("id must be a UUID")
        if not isinstance(event_date, date):
            raise TypeError("event_date must be a date")
        if operational_profile_id is not None and not isinstance(operational_profile_id, UUID):
            raise TypeError("operational_profile_id must be a UUID or None")
        if isinstance(operational_start_min, bool) or not isinstance(operational_start_min, int):
            raise TypeError("operational_start_min must be an integer")
        if operational_start_min < 0:
            raise ValueError("operational_start_min must be >= 0")
        if isinstance(operational_end_min, bool) or not isinstance(operational_end_min, int):
            raise TypeError("operational_end_min must be an integer")
        if operational_end_min <= operational_start_min:
            raise ValueError("operational_end_min must be greater than operational_start_min")
        if not isinstance(phases, tuple):
            raise TypeError("phases must be a tuple")
        if len(phases) < 1:
            raise ValueError("event_day must contain at least one phase")
        if not all(isinstance(p, EventDayPhase) for p in phases):
            raise TypeError("each phase must be an EventDayPhase instance")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, EventDay):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return (
            f"EventDay(id={self._id!r}, event_date={self._event_date!r}, "
            f"operational_profile_id={self._operational_profile_id!r}, "
            f"attendance_levels_count={len(self._attendance_levels)!r}, "
            f"operational_start_min={self._operational_start_min!r}, "
            f"operational_end_min={self._operational_end_min!r}, "
            f"phases_count={len(self._phases)})"
        )
