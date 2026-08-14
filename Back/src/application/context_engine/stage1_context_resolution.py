from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from src.application.context_engine.exceptions import InvalidPhaseContext
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_phase import OperationalPhase

LOCAL_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def _to_current_min(event_date: date, timestamp: datetime) -> int:
    local_ts = timestamp.astimezone(LOCAL_TZ)
    days_diff = (local_ts.date() - event_date).days
    return days_diff * 1440 + local_ts.hour * 60 + local_ts.minute


def _event_day_contains_minute(event_day: EventDay, timestamp: datetime) -> bool:
    """Verifica si el instante cae dentro de la ventana operativa de la jornada.

    `operational_start_min` / `operational_end_min` son minutos desde la
    medianoche de `event_day.event_date`; el límite superior es exclusivo:
    `[operational_start_min, operational_end_min)`.
    """
    current_min = _to_current_min(event_day.event_date, timestamp)
    return event_day.operational_start_min <= current_min < event_day.operational_end_min


async def resolve_active_event_day(
    timestamp: datetime,
    find_by_date: Callable[[date], Awaitable[EventDay | None]],
) -> EventDay | None:
    """Resuelve la jornada activa para un instante, soportando cruces de medianoche.

    Regla:
    1. timestamp convertido a America/Argentina/Buenos_Aires.
    2. Jornada de la fecha local (fecha civil argentina).
    3. Si el minuto actual cae en `[operational_start_min, operational_end_min)`,
       esa es la jornada activa.
    4. Si no, se evalúa la jornada del día anterior (permite jornadas que cruzan
       medianoche: un EventDay 14/08 con ventana [1200, 1680) sigue activo a la
       01:00 del 15/08).
    5. Si ninguna ventana contiene el instante, devuelve None (jornada inactiva).

    La selección NUNCA es únicamente por igualdad de fecha: depende de la ventana
    operativa. `find_by_date` recibe una fecha civil y devuelve el EventDay de esa
    fecha (o None); debe devolver entidades de dominio con `event_date`,
    `operational_start_min` y `operational_end_min`.
    """
    local_date = timestamp.astimezone(LOCAL_TZ).date()

    primary = await find_by_date(local_date)
    if primary is not None and _event_day_contains_minute(primary, timestamp):
        return primary

    previous = await find_by_date(local_date - timedelta(days=1))
    if previous is not None and _event_day_contains_minute(previous, timestamp):
        return previous

    return None


def resolve_contextual_phase(
    event_day: EventDay,
    operational_phases: Mapping[UUID, OperationalPhase],
    timestamp: datetime,
) -> tuple[EventDayPhase, OperationalPhase]:
    current_min = _to_current_min(event_day.event_date, timestamp)

    if not event_day.phases:
        raise InvalidPhaseContext(
            f"EventDay {event_day.id} has no phases"
        )

    for ed_phase in event_day.phases:
        if ed_phase.start_min <= current_min < ed_phase.end_min:
            try:
                op_phase = operational_phases[ed_phase.operational_phase_id]
            except KeyError:
                raise InvalidPhaseContext(
                    f"OperationalPhase {ed_phase.operational_phase_id} "
                    f"not found in operational phases index"
                )
            return ed_phase, op_phase

    raise InvalidPhaseContext(
        f"No EventDayPhase contains minute {current_min} "
        f"for EventDay {event_day.id}"
    )
