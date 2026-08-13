from datetime import date
from uuid import UUID, uuid4

from src.domain.entities.event_day_phase import EventDayPhase


class EventDay:
    """Concentra la configuracion operacional de una jornada.

    RFC-007: EventDay agrupa fecha, horario operativo, la referencia al
    AttendanceLevel seleccionado (attendance_level_id) y las fases
    (EventDayPhase). La evolucion temporal del evento pertenece a las fases.
    OperationalProfile queda deprecado como entidad de compatibilidad.
    """

    def __init__(
        self,
        event_date: date,
        operational_profile_id: UUID | None,
        operational_start_min: int,
        operational_end_min: int,
        phases: tuple[EventDayPhase, ...],
        attendance_level_id: UUID | None = None,
        id: UUID | None = None,
        estimated_vehicles: int | None = None,
        average_parking_duration: float | None = None,
    ) -> None:
        resolved_id = id if id is not None else uuid4()
        self._validate(
            resolved_id,
            event_date,
            operational_profile_id,
            attendance_level_id,
            operational_start_min,
            operational_end_min,
            phases,
            estimated_vehicles,
            average_parking_duration,
        )
        self._id = resolved_id
        self._event_date = event_date
        self._operational_profile_id = operational_profile_id
        self._attendance_level_id = attendance_level_id
        self._operational_start_min = operational_start_min
        self._operational_end_min = operational_end_min
        self._phases = phases
        self._estimated_vehicles = estimated_vehicles
        self._average_parking_duration = average_parking_duration

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
    def attendance_level_id(self) -> UUID | None:
        return self._attendance_level_id

    @property
    def operational_start_min(self) -> int:
        return self._operational_start_min

    @property
    def operational_end_min(self) -> int:
        return self._operational_end_min

    @property
    def phases(self) -> tuple[EventDayPhase, ...]:
        return self._phases

    @property
    def estimated_vehicles(self) -> int | None:
        return self._estimated_vehicles

    @property
    def average_parking_duration(self) -> float | None:
        return self._average_parking_duration

    @staticmethod
    def _validate(
        id: UUID,
        event_date: date,
        operational_profile_id: UUID,
        attendance_level_id: UUID,
        operational_start_min: int,
        operational_end_min: int,
        phases: tuple[EventDayPhase, ...],
        estimated_vehicles: int | None = None,
        average_parking_duration: float | None = None,
    ) -> None:
        if not isinstance(id, UUID):
            raise TypeError("id must be a UUID")
        if not isinstance(event_date, date):
            raise TypeError("event_date must be a date")
        if operational_profile_id is not None and not isinstance(operational_profile_id, UUID):
            raise TypeError("operational_profile_id must be a UUID or None")
        if attendance_level_id is not None and not isinstance(attendance_level_id, UUID):
            raise TypeError("attendance_level_id must be a UUID or None")
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
        if estimated_vehicles is not None:
            if isinstance(estimated_vehicles, bool) or not isinstance(estimated_vehicles, int):
                raise TypeError("estimated_vehicles must be an integer or None")
            if estimated_vehicles < 0:
                raise ValueError("estimated_vehicles must be >= 0")
        if average_parking_duration is not None:
            if (
                isinstance(average_parking_duration, bool)
                or not isinstance(average_parking_duration, float)
            ):
                raise TypeError("average_parking_duration must be a float or None")
            if average_parking_duration < 0.0:
                raise ValueError("average_parking_duration must be non-negative")

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
            f"attendance_level_id={self._attendance_level_id!r}, "
            f"operational_start_min={self._operational_start_min!r}, "
            f"operational_end_min={self._operational_end_min!r}, "
            f"phases_count={len(self._phases)})"
        )
