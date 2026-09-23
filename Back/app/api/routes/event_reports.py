from datetime import date, datetime
from typing import Literal, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TokenPayload, verify_token
from app.db.session import get_async_db
from app.models.event import Event
from app.models.event_day import EventDay
from app.models.event_day_phase import EventDayPhase
from app.models.operational_phase import OperationalPhase
from app.models.service_interaction_log import RESULT_STATUSES, ServiceInteractionLog
from app.models.zone import Zone
from app.schemas.event_reports import (
    CoverageGapItem,
    CoverageGapsResponse,
    EventSummaryResponse,
    PeriodRange,
    RecommendedZoneItem,
    RecommendedZonesResponse,
    ResultStatusCount,
    ServiceBreakdownItem,
    ServiceBreakdownResponse,
    TechnicalIncidentItem,
    TechnicalIncidentsResponse,
    TemporalBucket,
    TemporalDistributionBucket,
    TemporalDistributionResponse,
)

router = APIRouter(prefix="/api/events/{event_id}/reports", tags=["Informes Municipales"])


async def _get_event_or_404(db: AsyncSession, event_id: str) -> Event:
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _scope_conditions(
    event_id: str,
    start: Optional[datetime],
    end: Optional[datetime],
    service_category: Optional[str] = None,
):
    conditions = [ServiceInteractionLog.event_id == event_id]
    if start is not None:
        conditions.append(ServiceInteractionLog.timestamp >= start)
    if end is not None:
        conditions.append(ServiceInteractionLog.timestamp <= end)
    if service_category is not None:
        conditions.append(ServiceInteractionLog.service_category == service_category)
    return conditions


def _validate_timezone(timezone_name: str) -> None:
    try:
        ZoneInfo(timezone_name)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timezone")


async def _resolve_period(
    db: AsyncSession,
    event: Event,
    event_id: str,
    start: Optional[datetime],
    end: Optional[datetime],
) -> tuple[Optional[datetime], Optional[datetime]]:
    resolved_start = start if start is not None else event.start_date
    resolved_end = end if end is not None else event.end_date
    if resolved_start is None or resolved_end is None:
        result = await db.execute(
            select(
                func.min(ServiceInteractionLog.timestamp).label("min_ts"),
                func.max(ServiceInteractionLog.timestamp).label("max_ts"),
            ).where(ServiceInteractionLog.event_id == event_id)
        )
        min_ts, max_ts = result.one()
        if resolved_start is None:
            resolved_start = min_ts
        if resolved_end is None:
            resolved_end = max_ts
    return resolved_start, resolved_end


def _as_date(value: datetime):
    if isinstance(value, datetime):
        return value.date()
    return value


def _status_order_key(status: str) -> tuple:
    canonical = {s: i for i, s in enumerate(RESULT_STATUSES)}
    return canonical.get(status, len(RESULT_STATUSES)), status


@router.get("/summary", response_model=EventSummaryResponse)
async def event_report_summary(
    event_id: str,
    start: Optional[datetime] = Query(None, description="Inicio del período (ISO 8601)"),
    end: Optional[datetime] = Query(None, description="Fin del período (ISO 8601)"),
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    event = await _get_event_or_404(db, event_id)
    period_start, period_end = await _resolve_period(db, event, event_id, start, end)
    conditions = _scope_conditions(event_id, start, end)

    result = await db.execute(
        select(
            ServiceInteractionLog.result_status,
            func.count(ServiceInteractionLog.id),
        )
        .where(*conditions)
        .group_by(ServiceInteractionLog.result_status)
    )
    counts = {status: count for status, count in result.all()}
    total = sum(counts.values())

    breakdown = sorted(
        (
            ResultStatusCount(result_status=status, count=count)
            for status, count in counts.items()
        ),
        key=lambda item: _status_order_key(item.result_status),
    )

    return EventSummaryResponse(
        event_id=event.id,
        event_name=event.name,
        period=PeriodRange(start=period_start, end=period_end),
        total_consultas=total,
        with_results=counts.get("ok", 0),
        coverage_gaps_empty=counts.get("empty", 0),
        technical_errors=counts.get("error", 0),
        breakdown=breakdown,
    )


@router.get("/service_breakdown", response_model=ServiceBreakdownResponse)
async def event_report_service_breakdown(
    event_id: str,
    start: Optional[datetime] = Query(None, description="Inicio del período (ISO 8601)"),
    end: Optional[datetime] = Query(None, description="Fin del período (ISO 8601)"),
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    event = await _get_event_or_404(db, event_id)
    period_start, period_end = await _resolve_period(db, event, event_id, start, end)
    conditions = _scope_conditions(event_id, start, end)

    total_expr = func.count(ServiceInteractionLog.id)
    result = await db.execute(
        select(
            ServiceInteractionLog.service_category,
            total_expr.label("total_consultas"),
        )
        .where(*conditions)
        .group_by(ServiceInteractionLog.service_category)
        .order_by(total_expr.desc(), ServiceInteractionLog.service_category)
    )
    rows = result.all()
    overall = sum(row.total_consultas for row in rows)

    services = [
        ServiceBreakdownItem(
            service_category=row.service_category,
            total_consultas=row.total_consultas,
            percentage=round((row.total_consultas / overall) * 100, 2) if overall else 0.0,
        )
        for row in rows
    ]

    return ServiceBreakdownResponse(
        event_id=event.id,
        event_name=event.name,
        period=PeriodRange(start=period_start, end=period_end),
        services=services,
    )


@router.get("/coverage_gaps", response_model=CoverageGapsResponse)
async def event_report_coverage_gaps(
    event_id: str,
    start: Optional[datetime] = Query(None, description="Inicio del período (ISO 8601)"),
    end: Optional[datetime] = Query(None, description="Fin del período (ISO 8601)"),
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    event = await _get_event_or_404(db, event_id)
    period_start, period_end = await _resolve_period(db, event, event_id, start, end)
    conditions = _scope_conditions(event_id, start, end)

    total_expr = func.count(ServiceInteractionLog.id)
    empty_expr = func.count(ServiceInteractionLog.id).filter(
        ServiceInteractionLog.result_status == "empty"
    )
    result = await db.execute(
        select(
            ServiceInteractionLog.service_category,
            total_expr.label("total_consultas"),
            empty_expr.label("empty_count"),
        )
        .where(*conditions)
        .group_by(ServiceInteractionLog.service_category)
        .order_by(empty_expr.desc(), ServiceInteractionLog.service_category)
    )
    rows = result.all()

    services = [
        CoverageGapItem(
            service_category=row.service_category,
            total_consultas=row.total_consultas,
            empty_count=row.empty_count,
            empty_rate=round(row.empty_count / row.total_consultas, 4) 
            if row.total_consultas
            else 0.0,
        )
        for row in rows
    ]

    day_expr = func.date_trunc("day", ServiceInteractionLog.timestamp)
    temporal_result = await db.execute(
        select(day_expr.label("day"), empty_expr.label("count"))
        .where(*conditions)
        .group_by(day_expr)
        .order_by(day_expr)
    )
    temporal = [
        TemporalBucket(day=_as_date(row.day), count=row.count)
        for row in temporal_result.all()
    ]

    return CoverageGapsResponse(
        event_id=event.id,
        event_name=event.name,
        period=PeriodRange(start=period_start, end=period_end),
        services=services,
        temporal_distribution=temporal,
    )


@router.get("/technical_incidents", response_model=TechnicalIncidentsResponse)
async def event_report_technical_incidents(
    event_id: str,
    start: Optional[datetime] = Query(None, description="Inicio del período (ISO 8601)"),
    end: Optional[datetime] = Query(None, description="Fin del período (ISO 8601)"),
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    event = await _get_event_or_404(db, event_id)
    period_start, period_end = await _resolve_period(db, event, event_id, start, end)
    conditions = _scope_conditions(event_id, start, end)

    total_expr = func.count(ServiceInteractionLog.id)
    error_expr = func.count(ServiceInteractionLog.id).filter(
        ServiceInteractionLog.result_status == "error"
    )
    result = await db.execute(
        select(
            ServiceInteractionLog.service_category,
            total_expr.label("total_consultas"),
            error_expr.label("error_count"),
        )
        .where(*conditions)
        .group_by(ServiceInteractionLog.service_category)
        .order_by(error_expr.desc(), ServiceInteractionLog.service_category)
    )
    rows = result.all()

    services = [
        TechnicalIncidentItem(
            service_category=row.service_category,
            error_count=row.error_count,
            error_rate=round(row.error_count / row.total_consultas, 4)
            if row.total_consultas
            else 0.0,
        )
        for row in rows
    ]

    day_expr = func.date_trunc("day", ServiceInteractionLog.timestamp)
    temporal_result = await db.execute(
        select(day_expr.label("day"), error_expr.label("count"))
        .where(*conditions)
        .group_by(day_expr)
        .order_by(day_expr)
    )
    temporal = [
        TemporalBucket(day=_as_date(row.day), count=row.count)
        for row in temporal_result.all()
    ]

    return TechnicalIncidentsResponse(
        event_id=event.id,
        event_name=event.name,
        period=PeriodRange(start=period_start, end=period_end),
        services=services,
        temporal_distribution=temporal,
    )


async def _resolve_operational_phases(
    db: AsyncSession,
    event_id: str,
    buckets: list[datetime],
) -> dict[datetime, Optional[str]]:
    """Resuelve la fase operativa de cada bucket en memoria (sin N+1).

    Carga los EventDay de las fechas locales, sus event_day_phases y los
    nombres de operational_phases con 3 consultas acotadas; el intervalo
    [start_min, end_min) se resuelve contra la hora local del bucket.
    """
    local_dates: list[date] = sorted({bucket.date() for bucket in buckets})

    ed_result = await db.execute(
        select(EventDay).where(
            EventDay.event_id == event_id,
            EventDay.date.in_(local_dates),
        )
    )
    event_days = ed_result.scalars().all()
    event_day_by_id = {ed.id: ed for ed in event_days}

    phases_by_day: dict[date, list[EventDayPhase]] = {}
    op_ids: set[UUID] = set()
    if event_days:
        phase_result = await db.execute(
            select(EventDayPhase).where(
                EventDayPhase.event_day_id.in_([ed.id for ed in event_days])
            )
        )
        phases = phase_result.scalars().all()
        for phase in phases:
            ed = event_day_by_id.get(phase.event_day_id)
            if ed is not None:
                phases_by_day.setdefault(ed.date, []).append(phase)
                op_ids.add(phase.operational_phase_id)

    name_by_id: dict[UUID, str] = {}
    if op_ids:
        op_result = await db.execute(
            select(OperationalPhase).where(OperationalPhase.id.in_(list(op_ids)))
        )
        name_by_id = {op.id: op.name for op in op_result.scalars().all()}

    phase_by_bucket: dict[datetime, Optional[str]] = {}
    for bucket in buckets:
        day = bucket.date()
        minutes_of_day = bucket.hour * 60 + bucket.minute
        name: Optional[str] = None
        for phase in phases_by_day.get(day, []):
            if phase.start_min <= minutes_of_day < phase.end_min:
                name = name_by_id.get(phase.operational_phase_id)
                break
        phase_by_bucket[bucket] = name
    return phase_by_bucket


@router.get("/temporal_distribution", response_model=TemporalDistributionResponse)
async def event_report_temporal_distribution(
    event_id: str,
    start: Optional[datetime] = Query(None, description="Inicio del período (ISO 8601)"),
    end: Optional[datetime] = Query(None, description="Fin del período (ISO 8601)"),
    service_category: Optional[str] = Query(None, description="Filtrar por categoría de servicio"),
    granularity: Literal["hour", "day"] = Query("hour", description="Granularidad temporal"),
    timezone: str = Query(
        "America/Argentina/Buenos_Aires", description="Zona horaria local (IANA)"
    ),
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    _validate_timezone(timezone)
    event = await _get_event_or_404(db, event_id)
    period_start, period_end = await _resolve_period(db, event, event_id, start, end)
    conditions = _scope_conditions(event_id, start, end, service_category)

    local_ts = ServiceInteractionLog.timestamp.op("AT TIME ZONE")(timezone)
    if granularity == "hour":
        bucket_expr = func.date_trunc("hour", local_ts).label("bucket")
    else:
        bucket_expr = func.date_trunc("day", local_ts).label("bucket")
    count_expr = func.count(ServiceInteractionLog.id).label("count")

    agg_result = await db.execute(
        select(bucket_expr, count_expr)
        .where(*conditions)
        .group_by(bucket_expr)
        .order_by(bucket_expr)
    )
    rows = agg_result.all()

    if granularity == "hour":
        phase_by_bucket = await _resolve_operational_phases(
            db, event_id, [row.bucket for row in rows]
        )
        buckets = [
            TemporalDistributionBucket(
                bucket=row.bucket,
                count=row.count,
                phase=phase_by_bucket.get(row.bucket),
            )
            for row in rows
        ]
    else:
        buckets = [
            TemporalDistributionBucket(bucket=row.bucket, count=row.count)
            for row in rows
        ]

    return TemporalDistributionResponse(
        event_id=event.id,
        event_name=event.name,
        period=PeriodRange(start=period_start, end=period_end),
        granularity=granularity,
        timezone=timezone,
        service_category=service_category,
        buckets=buckets,
    )


@router.get("/recommended_zones", response_model=RecommendedZonesResponse)
async def event_report_recommended_zones(
    event_id: str,
    start: Optional[datetime] = Query(None, description="Inicio del período (ISO 8601)"),
    end: Optional[datetime] = Query(None, description="Fin del período (ISO 8601)"),
    service_category: Optional[str] = Query(None, description="Filtrar por categoría de servicio"),
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    event = await _get_event_or_404(db, event_id)
    period_start, period_end = await _resolve_period(db, event, event_id, start, end)
    conditions = _scope_conditions(event_id, start, end, service_category)

    zone_id_expr = func.jsonb_array_elements_text(
        ServiceInteractionLog.zone_ids
    ).label("zone_id")
    expanded = (
        select(ServiceInteractionLog.id.label("log_id"), zone_id_expr)
        .where(*conditions)
        .subquery()
    )
    rec_expr = func.count(func.distinct(expanded.c.log_id))

    result = await db.execute(
        select(
            Zone.id.label("zone_id"),
            Zone.name.label("zone_name"),
            Zone.type.label("zone_type"),
            rec_expr.label("recommendations"),
        )
        .join(Zone, Zone.id == expanded.c.zone_id)
        .group_by(Zone.id, Zone.name, Zone.type)
        .order_by(rec_expr.desc(), Zone.id)
    )
    rows = result.all()

    zones = [
        RecommendedZoneItem(
            zone_id=row.zone_id,
            zone_name=row.zone_name,
            zone_type=row.zone_type,
            recommendations=row.recommendations,
        )
        for row in rows
    ]

    return RecommendedZonesResponse(
        event_id=event.id,
        event_name=event.name,
        period=PeriodRange(start=period_start, end=period_end),
        service_category=service_category,
        zones=zones,
    )
