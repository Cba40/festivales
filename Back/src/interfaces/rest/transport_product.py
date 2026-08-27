"""REST adapter: deterministic transport recommendations based on real schedules.

Replaces the generic probabilistic RE with direct queries to transport V1 tables:
- transport_lines → transport_line_stops → transport_schedules → zones
"""
from __future__ import annotations

import logging
import math
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transport_line import TransportLine
from app.models.transport_line_stop import TransportLineStop
from app.models.transport_schedule import TransportSchedule
from app.models.zone import Zone
from app.schemas.product import (
    TransportRecommendationResponse,
    ZonaTransporteItem,
)

logger = logging.getLogger(__name__)

_EARTH_RADIUS_M = 6_371_000

ARGENTINA_TZ = ZoneInfo("America/Argentina/Buenos_Aires")


def _haversine_distance_m(
    lat1: float, lon1: float, lat2: float, lon2: float,
) -> float:
    """Great-circle distance between two coordinates in meters (Haversine)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return _EARTH_RADIUS_M * c


def _resolve_day_type(dt: datetime) -> str:
    """Map a datetime to a schedule day_type: weekday | saturday | sunday_holiday."""
    weekday = dt.weekday()
    if weekday == 5:
        return "saturday"
    if weekday == 6:
        return "sunday_holiday"
    return "weekday"


def _minutes_until(
    current_time: time,
    departure_time: time,
) -> int:
    """Minutes from *current_time* to *departure_time* (same day)."""
    current = current_time.hour * 60 + current_time.minute
    depart = departure_time.hour * 60 + departure_time.minute
    return depart - current


async def get_transport_product_adapter(
    db: AsyncSession,
    *,
    timestamp: datetime,
    event_id: str,
    destination: str | None = None,
    transport_type: str | None = None,
    user_latitude: float | None = None,
    user_longitude: float | None = None,
    limit: int = 5,
) -> TransportRecommendationResponse:
    """Deterministic transport recommendations from real schedule data.

    Logic:
    1. Load all transport_line_stops for this event, joining line + zone.
    2. If *transport_type* is provided, keep only stops of lines of that type.
    3. If *destination* is provided, keep only stops whose line has at least
       one schedule with that destination.
    4. For each stop, compute Haversine distance (if user coords available).
    5. For each stop, find the next departure after *timestamp* for the
       current day_type (civil calendar in Argentina time).
    6. Sort by distance ascending (stops without coordinates go last).
    7. Mark ``is_nearest=True`` on the first stop with valid coordinates.
    """
    now_local = timestamp.astimezone(ARGENTINA_TZ)
    day_type = _resolve_day_type(now_local)
    current_time = now_local.time()
    tomorrow_day_type = _resolve_day_type(now_local + timedelta(days=1))

    # --- 1. Load line_stops with line + zone metadata (single query) ---
    stmt = (
        select(
            TransportLineStop.id.label("line_stop_id"),
            TransportLineStop.stop_order,
            TransportLine.id.label("line_id"),
            TransportLine.name.label("line_name"),
            TransportLine.company,
            Zone.id.label("zone_id"),
            Zone.name.label("zone_name"),
            Zone.latitude,
            Zone.longitude,
            Zone.calle,
        )
        .join(TransportLine, TransportLineStop.line_id == TransportLine.id)
        .join(Zone, TransportLineStop.zone_id == Zone.id)
        .where(TransportLine.event_id == event_id)
        .where(TransportLine.active == True)
    )
    if transport_type is not None:
        stmt = stmt.where(TransportLine.type == transport_type)
    rows = (await db.execute(stmt)).all()

    if not rows:
        return TransportRecommendationResponse(
            event_id=event_id,
            timestamp=now_local.isoformat(),
            mode="sin_solucion",
            zonas=[],
        )

    # --- 2. If destination filter, find line_ids that serve it ---
    line_ids_with_dest: set[str] | None = None
    if destination is not None:
        dest_upper = destination.strip().upper()
        sched_stmt = (
            select(TransportSchedule.line_stop_id)
            .join(TransportLineStop, TransportLineStop.id == TransportSchedule.line_stop_id)
            .join(TransportLine, TransportLine.id == TransportLineStop.line_id)
            .where(TransportLine.event_id == event_id)
            .where(TransportSchedule.destination.ilike(f"%{dest_upper}%"))
        )
        matching_line_stop_ids = [r[0] for r in (await db.execute(sched_stmt)).all()]
        if not matching_line_stop_ids:
            return TransportRecommendationResponse(
                event_id=event_id,
                timestamp=now_local.isoformat(),
                mode="sin_solucion",
                zonas=[],
            )
        # Collect line_ids from matching line_stops
        ls_stmt = (
            select(TransportLineStop.line_id)
            .where(TransportLineStop.id.in_(matching_line_stop_ids))
        )
        line_ids_with_dest = {r[0] for r in (await db.execute(ls_stmt)).all()}
        rows = [r for r in rows if r.line_id in line_ids_with_dest]

    if not rows:
        return TransportRecommendationResponse(
            event_id=event_id,
            timestamp=now_local.isoformat(),
            mode="sin_solucion",
            zonas=[],
        )

    # --- 3. For each stop: load schedules (today + tomorrow), find next departure ---
    line_stop_ids = [r.line_stop_id for r in rows]
    today_scheds = await _load_schedules(db, line_stop_ids, day_type)
    tomorrow_scheds = await _load_schedules(db, line_stop_ids, tomorrow_day_type)

    # Group by line_stop_id, keeping today and tomorrow separate
    scheds_by_ls: dict[str, list] = {}
    scheds_by_ls_tomorrow: dict[str, list] = {}
    for s in today_scheds:
        scheds_by_ls.setdefault(s.line_stop_id, []).append(s)
    for s in tomorrow_scheds:
        scheds_by_ls_tomorrow.setdefault(s.line_stop_id, []).append(s)

    # --- 4. Build enriched items ---
    items: list[ZonaTransporteItem] = []
    for row in rows:
        lat, lng = row.latitude, row.longitude
        if lat is not None and lng is not None and user_latitude is not None and user_longitude is not None:
            distance_m = _haversine_distance_m(user_latitude, user_longitude, lat, lng)
        else:
            distance_m = float("inf")

        # Next departure for this stop (today first, then tomorrow)
        stop_scheds = scheds_by_ls.get(row.line_stop_id, [])
        stop_scheds_tomorrow = scheds_by_ls_tomorrow.get(row.line_stop_id, [])
        next_dep, mins_until, is_tomorrow = _find_next_departure(
            stop_scheds, stop_scheds_tomorrow, current_time
        )

        # If destination filter is active, filter matching destinations
        if destination is not None and next_dep is None:
            matching = [
                s for s in stop_scheds + stop_scheds_tomorrow
                if destination.strip().upper() in s.destination.upper()
            ]
            matching_today = [s for s in matching if s.day_type == day_type]
            matching_tomorrow = [s for s in matching if s.day_type == tomorrow_day_type]
            if matching_today or matching_tomorrow:
                next_dep, mins_until, is_tomorrow = _find_next_departure(
                    matching_today, matching_tomorrow, current_time
                )

        items.append(ZonaTransporteItem(
            zone_id=str(row.zone_id),
            name=row.zone_name or str(row.zone_id),
            score=1.0 if next_dep is not None else 0.0,
            reasoning=_build_reasoning(row, next_dep, mins_until, distance_m, is_tomorrow),
            saturation_level=None,
            estado=None,
            availability=None,
            estimated_wait=mins_until,
            confidence=None,
            active_restriction="OPEN",
            operational_state="HAS_SERVICE" if next_dep is not None else "NO_SERVICE",
            lat=lat,
            lng=lng,
            referencia=row.calle or row.zone_name or "",
            distancia_min=round(distance_m) if distance_m != float("inf") else None,
            is_nearest=False,
            calle=row.calle or "",
            line_name=row.line_name,
            company=row.company,
            next_departure=next_dep,
            minutes_until_next=mins_until,
            destination=destination,
            is_tomorrow=is_tomorrow,
        ))

    # --- 5. Sort by distance (None/inf last) ---
    items.sort(key=lambda z: z.distancia_min if z.distancia_min is not None else float("inf"))

    # --- 6. Mark is_nearest on first item with valid coordinates ---
    for item in items:
        if item.lat is not None and item.lng is not None:
            item.is_nearest = True
            break

    # --- 7. Truncate to limit ---
    items = items[:limit]

    # --- 8. Determine mode ---
    mode = _compute_mode(items)

    return TransportRecommendationResponse(
        event_id=event_id,
        timestamp=now_local.isoformat(),
        mode=mode,
        zonas=items,
    )


async def _load_schedules(
    db: AsyncSession,
    line_stop_ids: list[str],
    day_type: str,
) -> list:
    """Load all schedules for given line_stop_ids and day_type."""
    if not line_stop_ids:
        return []
    stmt = (
        select(TransportSchedule)
        .where(
            and_(
                TransportSchedule.line_stop_id.in_(line_stop_ids),
                TransportSchedule.day_type == day_type,
            )
        )
        .order_by(TransportSchedule.departure_time)
    )
    return (await db.execute(stmt)).scalars().all()


def _minutes_to_midnight(current_time: time) -> int:
    """Minutes from *current_time* until the next midnight (23:59:59 -> 0)."""
    current = current_time.hour * 60 + current_time.minute
    return 24 * 60 - current


def _extract_time(value) -> time:
    return value if isinstance(value, time) else value.time()


def _find_next_departure(
    schedules: list,
    schedules_tomorrow: list,
    current_time: time,
) -> tuple[str | None, int | None, bool]:
    """Find the next departure today, else the first departure tomorrow.

    Returns ``(HH:MM, minutes_until, is_tomorrow)``.
    ``is_tomorrow`` is True when the match comes from the following day.
    """
    # 1. Try today: first departure after current_time
    for sched in schedules:
        dep_time = _extract_time(sched.departure_time)
        mins = _minutes_until(current_time, dep_time)
        if mins > 0:
            return dep_time.strftime("%H:%M"), mins, False

    # 2. No more services today: first departure tomorrow.
    #    Minutes = time-to-midnight + departure minutes after midnight.
    base_minutes = _minutes_to_midnight(current_time)
    for sched in schedules_tomorrow:
        dep_time = _extract_time(sched.departure_time)
        dep_minutes = dep_time.hour * 60 + dep_time.minute
        return dep_time.strftime("%H:%M"), base_minutes + dep_minutes, True

    # 3. No service today nor tomorrow
    return None, None, False


def _build_reasoning(
    row, next_dep: str | None, mins: int | None, distance_m: float,
    is_tomorrow: bool = False,
) -> list[str]:
    """Build human-readable reasoning for the recommendation."""
    reasons = []
    if next_dep is not None:
        prefijo = "mañana " if is_tomorrow else ""
        reasons.append(f"Próximo servicio {prefijo}a las {next_dep} en {mins} min")
    else:
        reasons.append("Sin horarios disponibles para este horario")
    if distance_m != float("inf"):
        reasons.append(f"Distancia: {round(distance_m)}m")
    return reasons


def _compute_mode(zonas: list[ZonaTransporteItem]) -> str:
    """Determine display mode from zone list."""
    if not zonas:
        return "sin_solucion"
    all_no_service = all(z.operational_state == "NO_SERVICE" for z in zonas)
    if all_no_service:
        return "sin_solucion"
    return "informar"
