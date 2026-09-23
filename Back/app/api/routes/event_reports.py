from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TokenPayload, verify_token
from app.db.session import get_async_db
from app.models.event import Event
from app.models.service_interaction_log import RESULT_STATUSES, ServiceInteractionLog
from app.schemas.event_reports import (
    CoverageGapItem,
    CoverageGapsResponse,
    EventSummaryResponse,
    PeriodRange,
    ResultStatusCount,
    ServiceBreakdownItem,
    ServiceBreakdownResponse,
    TechnicalIncidentItem,
    TechnicalIncidentsResponse,
    TemporalBucket,
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
):
    conditions = [ServiceInteractionLog.event_id == event_id]
    if start is not None:
        conditions.append(ServiceInteractionLog.timestamp >= start)
    if end is not None:
        conditions.append(ServiceInteractionLog.timestamp <= end)
    return conditions


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
