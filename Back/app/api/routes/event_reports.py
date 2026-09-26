from bisect import bisect_right
from datetime import date, datetime
from typing import Any, Literal, NamedTuple, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, join, select
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import Function
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TokenPayload, verify_token
from app.db.session import get_async_db
from app.models.event import Event
from app.models.event_day import EventDay
from app.models.event_day_phase import EventDayPhase
from app.models.operational_event import OperationalEvent
from app.models.operational_phase import OperationalPhase
from app.models.service_interaction_log import RESULT_STATUSES, ServiceInteractionLog
from app.models.zone import Zone
from app.schemas.event_reports import (
    CoverageGapItem,
    CoverageGapsResponse,
    EventSummaryResponse,
    FilterBreakdownItem,
    ObservationsPhase,
    OperationalEventSummaryItem,
    OperationalEventsPhase,
    OperationalPhaseRef,
    OperationalProfileResponse,
    PeriodRange,
    PlatformQueriesPhase,
    PredictionsPhase,
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
    ZoneAnalysisItem,
    ZoneAnalysisResponse,
    ZoneObservationSummary,
    ZonePredictionSummary,
)
from src.infrastructure.persistence.models.operational_observation import (
    OperationalObservationModel,
)
from src.infrastructure.persistence.models.prediction import PredictionModel

router = APIRouter(prefix="/api/events/{event_id}/reports", tags=["Informes Municipales"])


async def _get_event_or_404(db: AsyncSession, event_id: str) -> Event:
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


PERIOD_MODE_REQUESTED = "requested"
PERIOD_MODE_EVENT = "event"
PERIOD_MODE_ACCUMULATED = "accumulated"


class EffectivePeriod(NamedTuple):
    """Período efectivo único: alimenta la respuesta y el filtro SQL."""

    start: Optional[datetime]
    end: Optional[datetime]
    mode: str


def _resolve_period(
    event: Event,
    start: Optional[datetime],
    end: Optional[datetime],
) -> EffectivePeriod:
    """Resuelve el período efectivo sin consultar los datos a medir.

    1. ``requested``: el llamador declaró al menos un extremo.
    2. ``event``: no hay parámetros, pero el evento declara al menos un extremo.
    3. ``accumulated``: no hay período declarado; histórico sin filtro de rango.

    Ningún modo deriva el rango de ``service_interaction_log``: el histórico se
    expresa como ausencia de predicado de timestamp, nunca como min/max del
    mismo conjunto que luego se filtra.
    """
    if start is not None or end is not None:
        return EffectivePeriod(start, end, PERIOD_MODE_REQUESTED)
    if event.start_date is not None or event.end_date is not None:
        return EffectivePeriod(event.start_date, event.end_date, PERIOD_MODE_EVENT)
    return EffectivePeriod(None, None, PERIOD_MODE_ACCUMULATED)


def _scope_conditions(
    event_id: str,
    period: EffectivePeriod,
    service_category: Optional[str] = None,
):
    conditions = [ServiceInteractionLog.event_id == event_id]
    if period.start is not None:
        conditions.append(ServiceInteractionLog.timestamp >= period.start)
    if period.end is not None:
        conditions.append(ServiceInteractionLog.timestamp <= period.end)
    if service_category is not None:
        conditions.append(ServiceInteractionLog.service_category == service_category)
    return conditions


# Filtro canónico de actividad real del usuario: eventos explícitos emitidos
# por la PWA pública (apertura de pantalla / cambio de filtro), nunca requests
# técnicas (las de los productos → interaction_type='request').
USER_ACTIVITY_TYPES = ("screen_open", "filter_change")

# Prefijo que emite la PWA cuando el usuario elige una zona concreta
# (Estacionar.handleSelectZona y ServiciosGenerales.handleSelectBathroom).
# El valor completo es `zona=<zone_id>`; de ahí se extrae el id con split_part.
ZONE_SELECT_PREFIX = "zona="


def _activity_conditions(
    event_id: str,
    period: EffectivePeriod,
    service_category: Optional[str] = None,
):
    conditions = _scope_conditions(event_id, period, service_category)
    conditions.append(ServiceInteractionLog.interaction_type.in_(USER_ACTIVITY_TYPES))
    conditions.append(ServiceInteractionLog.origin == "user")
    return conditions


def _request_conditions(
    event_id: str,
    period: EffectivePeriod,
    service_category: Optional[str] = None,
):
    conditions = _scope_conditions(event_id, period, service_category)
    conditions.append(ServiceInteractionLog.interaction_type == "request")
    return conditions


class _JsonbOrdinality(Function):
    """``jsonb_array_elements_text(x) WITH ORDINALITY`` sin alias.

    La posición en el array ``zone_ids`` es el ranking que el recomendador
    asignó a cada zona. Sin ella, todas las zonas que siempre viajan juntas (el
    mismo set de la misma respuesta) quedan con idéntico conteo y la tabla no
    discrimina nada.

    Dos trampas de SQLAlchemy 2.0 que esta clase tiene que evitar:

    1. El alias lo emite ``table_valued(name="t")``. Acá NO se escribe a mano: si
       el render incluye su propio ``AS t(...)``, ``table_valued`` agrega después
       un ``AS anon_N`` y Postgres responde ``syntax error at or near "AS"``.
    2. El ``super().__init__`` es obligatorio. Sin él, ``clause_expr`` nunca se
       crea y el generador de claves de caché revienta con
       ``AttributeError: Neither '_JsonbOrdinality' object nor 'Comparator'
       object has an attribute 'clause_expr'``. Ojo: ``str(stmt.compile())``
       sigue funcionando, así que el fallo solo aparece cuando el engine real
       arma la clave de caché.

    Los nombres ``value`` y ``ordinality`` son los que Postgres asigna por
    defecto a esta función; no hace falta declararlos.

    Nota: ``CAST(zone_ids AS text[])`` NO sirve; Postgres responde CannotCoerce
    porque jsonb no castea a array de forma implícita.
    """

    inherit_cache = True

    def __init__(self, arg, **kwargs):
        super().__init__(arg, **kwargs)
        self.arg = arg


@compiles(_JsonbOrdinality)
def _compile_jsonb_ordinality(element, compiler, **kw):
    return f"jsonb_array_elements_text({compiler.process(element.arg, **kw)}) WITH ORDINALITY"


def _expanded_zone_positions(conditions):
    """Expande ``zone_ids`` en una fila por (request, zona) con su posición."""
    elements = _JsonbOrdinality(ServiceInteractionLog.zone_ids).table_valued(
        "value", "ordinality", name="t"
    )
    return select(
        ServiceInteractionLog.id.label("log_id"),
        elements.c.value.label("zone_id"),
        elements.c.ordinality.label("position"),
    ).where(*conditions)


def _validate_timezone(timezone_name: str) -> None:
    try:
        ZoneInfo(timezone_name)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timezone")


def _require_absolute_bounds(
    start: Optional[datetime],
    end: Optional[datetime],
) -> None:
    """Rechaza extremos de período sin offset.

    ``service_interaction_log.timestamp`` es ``timestamptz``: un extremo naive
    lo interpretaría Postgres en la zona de sesión y podría truncar o extender
    el día local. El contrato es que el cliente convierta primero el día/período
    local a instantes absolutos (UTC) y los envíe con offset.
    """
    naive = [
        name
        for name, value in (("start", start), ("end", end))
        if value is not None and value.tzinfo is None
    ]
    if naive:
        raise HTTPException(
            status_code=400,
            detail=(
                "Period bounds must be absolute instants with a UTC offset "
                f"(naive: {', '.join(naive)})."
            ),
        )


def _as_date(value: datetime):
    if isinstance(value, datetime):
        return value.date()
    return value


def _local_date(value: Optional[datetime], zi: ZoneInfo) -> Optional[date]:
    """Fecha local (IANA) de un extremo del período.

    Se usa para acotar ``EventDay.date``, que es una fecha local, contra el
    período efectivo. Un extremo naive se interpreta como fecha ya local.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.date()
    return value.astimezone(zi).date()


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
    period = _resolve_period(event, start, end)
    conditions = _activity_conditions(event_id, period)

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
        period=PeriodRange(start=period.start, end=period.end, mode=period.mode),
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
    period = _resolve_period(event, start, end)
    conditions = _activity_conditions(event_id, period)

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

    filter_result = await db.execute(
        select(
            ServiceInteractionLog.request_mode,
            func.count(ServiceInteractionLog.id).label("total"),
        )
        .where(*conditions)
        .group_by(ServiceInteractionLog.request_mode)
        .order_by(func.count(ServiceInteractionLog.id).desc())
    )
    filters = [
        FilterBreakdownItem(request_mode=row.request_mode, total=row.total)
        for row in filter_result.all()
    ]

    return ServiceBreakdownResponse(
        event_id=event.id,
        event_name=event.name,
        period=PeriodRange(start=period.start, end=period.end, mode=period.mode),
        services=services,
        filters=filters,
    )


@router.get("/coverage_gaps", response_model=CoverageGapsResponse)
async def event_report_coverage_gaps(
    event_id: str,
    start: Optional[datetime] = Query(None, description="Inicio del período (ISO 8601)"),
    end: Optional[datetime] = Query(None, description="Fin del período (ISO 8601)"),
    origin: Optional[Literal["user", "prefetch", "system"]] = Query(
        None,
        description=(
            "Filtrar por origen del request: user (intención), prefetch (precarga) "
            "o system (polling/SWR). Sin valor, incluye todos."
        ),
    ),
    timezone: str = Query(
        "America/Argentina/Buenos_Aires", description="Zona horaria local (IANA)"
    ),
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    _validate_timezone(timezone)
    event = await _get_event_or_404(db, event_id)
    period = _resolve_period(event, start, end)
    conditions = _request_conditions(event_id, period)
    if origin is not None:
        conditions.append(ServiceInteractionLog.origin == origin)

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

    # Bucketing en hora local: un request de las 23:00 ART debe caer en su día
    # local, no en el siguiente por usar UTC.
    local_ts = ServiceInteractionLog.timestamp.op("AT TIME ZONE")(timezone)
    day_expr = func.date_trunc("day", local_ts)
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
        period=PeriodRange(start=period.start, end=period.end, mode=period.mode),
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
    period = _resolve_period(event, start, end)
    conditions = _request_conditions(event_id, period)

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
        period=PeriodRange(start=period.start, end=period.end, mode=period.mode),
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
    request_mode_prefix: Optional[str] = Query(
        None,
        description="Filtrar por prefijo de request_mode (ej: salida_vehicular=)",
    ),
    granularity: Literal["hour", "day"] = Query("hour", description="Granularidad temporal"),
    timezone: str = Query(
        "America/Argentina/Buenos_Aires", description="Zona horaria local (IANA)"
    ),
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    _validate_timezone(timezone)
    _require_absolute_bounds(start, end)
    event = await _get_event_or_404(db, event_id)
    period = _resolve_period(event, start, end)
    conditions = _activity_conditions(event_id, period, service_category)
    if request_mode_prefix is not None:
        escaped = (
            request_mode_prefix.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )
        conditions.append(
            ServiceInteractionLog.request_mode.like(f"{escaped}%", escape="\\")
        )

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

    # El detalle por request_mode solo se calcula cuando el operador ya eligió un
    # servicio: sobre el total general la respuesta sería demasiado pesada y los
    # modos no son comparables entre categorías.
    breakdown_by_bucket: Optional[dict[datetime, list[dict[str, Any]]]] = None
    if service_category is not None:
        detail_result = await db.execute(
            select(bucket_expr, ServiceInteractionLog.request_mode, count_expr)
            .where(*conditions)
            .group_by(bucket_expr, ServiceInteractionLog.request_mode)
            .order_by(bucket_expr, count_expr.desc())
        )
        breakdown_by_bucket = {}
        for detail in detail_result.all():
            breakdown_by_bucket.setdefault(detail.bucket, []).append(
                {"request_mode": detail.request_mode, "count": detail.count}
            )

    if granularity == "hour":
        phase_by_bucket = await _resolve_operational_phases(
            db, event_id, [row.bucket for row in rows]
        )
        buckets = [
            TemporalDistributionBucket(
                bucket=row.bucket,
                count=row.count,
                phase=phase_by_bucket.get(row.bucket),
                breakdown=(
                    breakdown_by_bucket.get(row.bucket) if breakdown_by_bucket is not None else None
                ),
            )
            for row in rows
        ]
    else:
        buckets = [
            TemporalDistributionBucket(
                bucket=row.bucket,
                count=row.count,
                breakdown=(
                    breakdown_by_bucket.get(row.bucket) if breakdown_by_bucket is not None else None
                ),
            )
            for row in rows
        ]

    return TemporalDistributionResponse(
        event_id=event.id,
        event_name=event.name,
        period=PeriodRange(start=period.start, end=period.end, mode=period.mode),
        granularity=granularity,
        timezone=timezone,
        service_category=service_category,
        buckets=buckets,
    )


@router.get("/zone_analysis", response_model=ZoneAnalysisResponse)
async def event_report_zone_analysis(
    event_id: str,
    start: Optional[datetime] = Query(None, description="Inicio del período (ISO 8601)"),
    end: Optional[datetime] = Query(None, description="Fin del período (ISO 8601)"),
    service_category: Optional[str] = Query(None, description="Filtrar por categoría de servicio"),
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    """Combina demanda real del usuario y cobertura del sistema por zona.

    Son dos preguntas distintas sobre el mismo catálogo de zonas:

    * ``real_choices`` mide demanda: cuántos usuarios eligieron la zona
      (``filter_change`` con ``origin=user`` y ``request_mode='zona=<id>'``).
      Solo existe para los módulos que instrumentaron el clic.
    * ``recommendation_count`` y ``avg_position`` miden oferta: cuántas requests
      técnicas la devolvieron y en qué posición del ranking, 1-based.

    Antes vivían separadas y la de cobertura, al no tener posición, producía el
    mismo número para todas las zonas que siempre viajan en la misma respuesta.
    """
    _require_absolute_bounds(start, end)
    event = await _get_event_or_404(db, event_id)
    period = _resolve_period(event, start, end)

    # --- Demanda real: la zona sale del propio request_mode, no de zone_ids ---
    choice_conditions = _activity_conditions(event_id, period, service_category)
    zone_from_mode = func.split_part(ServiceInteractionLog.request_mode, "=", 2).label("zone_id")
    choices_result = await db.execute(
        select(zone_from_mode, func.count(ServiceInteractionLog.id).label("real_choices"))
        .where(*choice_conditions, ServiceInteractionLog.request_mode.like(f"{ZONE_SELECT_PREFIX}%"))
        .group_by(zone_from_mode)
    )
    real_choices = {row.zone_id: row.real_choices for row in choices_result.all()}

    # --- Cobertura: posición real dentro del array zone_ids de cada request ---
    request_conditions = _request_conditions(event_id, period, service_category)
    expanded = _expanded_zone_positions(request_conditions).subquery()
    coverage_result = await db.execute(
        select(
            Zone.id.label("zone_id"),
            Zone.name.label("zone_name"),
            Zone.type.label("zone_type"),
            func.count(func.distinct(expanded.c.log_id)).label("recommendation_count"),
            func.avg(expanded.c.position).label("avg_position"),
        )
        .select_from(join(Zone, expanded, Zone.id == expanded.c.zone_id))
        .where(Zone.event_id == event_id)
        .group_by(Zone.id, Zone.name, Zone.type)
    )
    coverage = {
        row.zone_id: (row.zone_name, row.zone_type, row.recommendation_count, row.avg_position)
        for row in coverage_result.all()
    }

    zones = [
        ZoneAnalysisItem(
            zone_id=zone_id,
            zone_name=name,
            zone_type=zone_type,
            real_choices=real_choices.get(zone_id, 0),
            recommendation_count=recommendation_count,
            avg_position=avg_position,
        )
        for zone_id, (name, zone_type, recommendation_count, avg_position) in coverage.items()
    ]
    # Demanda primero; después, las más recomendadas arriba. Las zonas que nunca
    # se recomendaron (avg_position nulo) quedan al final en vez de ir primero.
    zones.sort(
        key=lambda zone: (
            -zone.real_choices,
            zone.avg_position if zone.avg_position is not None else float("inf"),
            zone.zone_name,
        )
    )

    return ZoneAnalysisResponse(
        event_id=event.id,
        event_name=event.name,
        period=PeriodRange(start=period.start, end=period.end, mode=period.mode),
        service_category=service_category,
        zones=zones,
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
    period = _resolve_period(event, start, end)
    conditions = _request_conditions(event_id, period, service_category)

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
        period=PeriodRange(start=period.start, end=period.end, mode=period.mode),
        service_category=service_category,
        zones=zones,
    )


def _resolve_phase_for_minute(
    minute_of_day: int,
    day_id: Optional[str],
    phases_by_day_id: dict[str, tuple[list[int], list[tuple[int, int, UUID]]]],
) -> Optional[UUID]:
    """Resuelve la fase operativa de un minuto local (bisect, O(log ph))."""
    bounds = phases_by_day_id.get(day_id)
    if not bounds or not bounds[1]:
        return None
    starts, items = bounds
    index = bisect_right(starts, minute_of_day) - 1
    if index < 0:
        return None
    start_min, end_min, phase_id = items[index]
    if start_min <= minute_of_day < end_min:
        return phase_id
    return None


def _resolve_phase_for_datetime(
    local_dt: datetime,
    day_by_date: dict[date, EventDay],
    phases_by_day_id: dict[str, tuple[list[int], list[tuple[int, int, UUID]]]],
) -> Optional[UUID]:
    day = day_by_date.get(local_dt.date())
    if day is None:
        return None
    return _resolve_phase_for_minute(
        local_dt.hour * 60 + local_dt.minute,
        day.id,
        phases_by_day_id,
    )


async def _load_event_day_phases(
    db: AsyncSession,
    day_ids: list[str],
    event_days: list[EventDay],
) -> tuple[dict[date, EventDay], dict[str, tuple[list[int], list[tuple[int, int, UUID]]]]]:
    """Carga event_day_phases en 1 consulta y arma índices de resolución por día."""
    day_by_date = {ed.date: ed for ed in event_days}
    phases_by_day_id: dict[str, tuple[list[int], list[tuple[int, int, UUID]]]] = {}
    if not day_ids:
        return day_by_date, phases_by_day_id
    row_result = await db.execute(
        select(EventDayPhase).where(EventDayPhase.event_day_id.in_(day_ids))
    )
    for phase in row_result.scalars().all():
        if phase.event_day_id not in phases_by_day_id:
            phases_by_day_id[phase.event_day_id] = ([], [])
        phases_by_day_id[phase.event_day_id][1].append(
            (phase.start_min, phase.end_min, phase.operational_phase_id)
        )
    for bounds in phases_by_day_id.values():
        bounds[1].sort(key=lambda item: item[0])
        bounds[0][:] = [item[0] for item in bounds[1]]
    return day_by_date, phases_by_day_id


def _phase_sort_key(
    phase_id: Optional[UUID],
    sort_by_id: dict[UUID, int],
    name_by_id: dict[UUID, str],
) -> tuple:
    if phase_id is None:
        return (10**9, "")
    return (sort_by_id.get(phase_id, 10**9), name_by_id.get(phase_id, str(phase_id)))


@router.get("/operational_profile", response_model=OperationalProfileResponse)
async def event_report_operational_profile(
    event_id: str,
    start: Optional[datetime] = Query(None, description="Inicio del período (ISO 8601)"),
    end: Optional[datetime] = Query(None, description="Fin del período (ISO 8601)"),
    timezone: str = Query(
        "America/Argentina/Buenos_Aires", description="Zona horaria local (IANA)"
    ),
    db: AsyncSession = Depends(get_async_db),
    _: TokenPayload = Depends(verify_token),
):
    _validate_timezone(timezone)
    event = await _get_event_or_404(db, event_id)
    period = _resolve_period(event, start, end)
    zi = ZoneInfo(timezone)

    day_conditions = [EventDay.event_id == event_id]
    local_start_date = _local_date(period.start, zi)
    if local_start_date is not None:
        day_conditions.append(EventDay.date >= local_start_date)
    local_end_date = _local_date(period.end, zi)
    if local_end_date is not None:
        day_conditions.append(EventDay.date <= local_end_date)
    day_result = await db.execute(select(EventDay).where(*day_conditions))
    event_days = day_result.scalars().all()
    day_ids = [ed.id for ed in event_days]
    profile_ids = {
        ed.operational_profile_id for ed in event_days if ed.operational_profile_id is not None
    }

    day_by_date, phases_by_day_id = await _load_event_day_phases(db, day_ids, event_days)

    op_phases: list = []
    if profile_ids:
        op_result = await db.execute(
            select(OperationalPhase).where(
                OperationalPhase.operational_profile_id.in_(list(profile_ids))
            )
        )
        op_phases = list(op_result.scalars().all())

    known_ids = {op.id for op in op_phases}
    name_by_id: dict[UUID, str] = {op.id: op.name for op in op_phases}

    predictions = []
    if day_ids:
        pred_result = await db.execute(
            select(PredictionModel)
            .where(PredictionModel.event_day_id.in_(day_ids))
            .order_by(PredictionModel.timestamp)
        )
        predictions = pred_result.scalars().all()

        missing_ids = {
            pred.active_phase_id
            for pred in predictions
            if pred.active_phase_id not in known_ids
        }
        if missing_ids:
            extra_result = await db.execute(
                select(OperationalPhase).where(OperationalPhase.id.in_(list(missing_ids)))
            )
            op_phases = list(op_phases) + list(extra_result.scalars().all())
            name_by_id = {op.id: op.name for op in op_phases}

    observations = []
    if day_ids:
        obs_result = await db.execute(
            select(OperationalObservationModel).where(
                OperationalObservationModel.event_day_id.in_(day_ids)
            )
        )
        observations = obs_result.scalars().all()

    operational_events = []
    if day_ids:
        ev_result = await db.execute(
            select(OperationalEvent).where(
                OperationalEvent.event_day_id.in_(day_ids)
            )
        )
        operational_events = ev_result.scalars().all()

    zone_result = await db.execute(select(Zone).where(Zone.event_id == event_id))
    zone_by_id = {zone.id: zone.name for zone in zone_result.scalars().all()}

    local_ts = ServiceInteractionLog.timestamp.op("AT TIME ZONE")(timezone)
    hour_expr = func.date_trunc("hour", local_ts).label("hour")
    agg_result = await db.execute(
        select(
            hour_expr,
            ServiceInteractionLog.service_category,
            ServiceInteractionLog.result_status,
            func.count(ServiceInteractionLog.id).label("count"),
        )
        .where(*_activity_conditions(event_id, period))
        .group_by(
            hour_expr,
            ServiceInteractionLog.service_category,
            ServiceInteractionLog.result_status,
        )
    )
    agg_rows = agg_result.all()

    sort_phases = sorted(op_phases, key=lambda op: (op.sort_order, op.name))
    sort_by_id = {op.id: index for index, op in enumerate(sort_phases)}

    platform_totals: dict[Optional[UUID], dict[str, int]] = {}
    for row in agg_rows:
        phase_id = _resolve_phase_for_datetime(row.hour, day_by_date, phases_by_day_id)
        acc = platform_totals.setdefault(
            phase_id, {"consultas_total": 0, "with_results": 0, "empty": 0, "unavailable": 0, "error": 0}
        )
        acc["consultas_total"] += row.count
        status_key = {"ok": "with_results", "empty": "empty", "unavailable": "unavailable"}.get(
            row.result_status, "error"
        )
        acc[status_key] += row.count

    pred_counts: dict[Optional[UUID], int] = {}
    zone_states: dict[tuple[Optional[UUID], Optional[str]], dict] = {}
    for pred in predictions:
        phase_id = pred.active_phase_id
        pred_counts[phase_id] = pred_counts.get(phase_id, 0) + 1
        zone_states_data = pred.zone_states_data
        if isinstance(zone_states_data, str):
            import json

            zone_states_data = json.loads(zone_states_data)
        for zone_state in zone_states_data or []:
            zone_id = zone_state.get("zone_id")
            if not zone_id:
                continue
            key = (phase_id, zone_id)
            previous = zone_states.get(key)
            if previous is None or pred.timestamp >= previous["timestamp"]:
                zone_states[key] = {
                    "timestamp": pred.timestamp,
                    "projected_density": zone_state.get("projected_density"),
                    "operational_state": zone_state.get("operational_state"),
                }

    obs_zone_agg: dict[tuple[Optional[UUID], Optional[str]], list[int]] = {}
    obs_count: dict[Optional[UUID], int] = {}
    obs_unassigned = 0
    for obs in observations:
        local_dt = obs.timestamp.astimezone(zi)
        phase_id = _resolve_phase_for_datetime(local_dt, day_by_date, phases_by_day_id)
        obs_count[phase_id] = obs_count.get(phase_id, 0) + 1
        if phase_id is None:
            obs_unassigned += 1
        key = (phase_id, obs.zone_id)
        acc = obs_zone_agg.setdefault(key, [0, 0])
        acc[0] += 1
        acc[1] += obs.observed_density

    events_by_phase: dict[Optional[UUID], list] = {}
    incidents_by_phase: dict[Optional[UUID], int] = {}
    events_unassigned = 0
    for operational_event in operational_events:
        local_dt = operational_event.start_timestamp.astimezone(zi)
        phase_id = _resolve_phase_for_datetime(local_dt, day_by_date, phases_by_day_id)
        events_by_phase.setdefault(phase_id, []).append(operational_event)
        incidents_by_phase[phase_id] = incidents_by_phase.get(phase_id, 0) + int(
            operational_event.is_incident
        )
        if phase_id is None:
            events_unassigned += 1

    present_phase_ids = (
        set(platform_totals) | set(pred_counts) | set(obs_count) | set(events_by_phase)
    )
    ordered_phase_ids = sorted(
        present_phase_ids, key=lambda pid: _phase_sort_key(pid, sort_by_id, name_by_id)
    )

    def phase_name(phase_id: Optional[UUID]) -> str:
        if phase_id is None:
            return "unassigned"
        return name_by_id.get(phase_id, str(phase_id))

    phases = [
        OperationalPhaseRef(
            phase_id=str(phase_id) if phase_id is not None else None,
            phase_name=phase_name(phase_id),
        )
        for phase_id in ordered_phase_ids
    ]

    platform_queries = [
        PlatformQueriesPhase(
            phase_id=str(phase_id) if phase_id is not None else None,
            phase_name=phase_name(phase_id),
            consultas_total=platform_totals[phase_id]["consultas_total"],
            with_results=platform_totals[phase_id]["with_results"],
            empty=platform_totals[phase_id]["empty"],
            unavailable=platform_totals[phase_id]["unavailable"],
            error=platform_totals[phase_id]["error"],
        )
        for phase_id in ordered_phase_ids
        if phase_id in platform_totals
    ]

    predictions_summary = []
    for phase_id in ordered_phase_ids:
        if phase_id not in pred_counts:
            continue
        zones = []
        for (zone_phase_id, zone_id), state in zone_states.items():
            if zone_phase_id != phase_id:
                continue
            zones.append(
                ZonePredictionSummary(
                    zone_id=zone_id,
                    zone_name=zone_by_id.get(zone_id, zone_id),
                    projected_density=state["projected_density"],
                    operational_state=state["operational_state"],
                )
            )
        predictions_summary.append(
            PredictionsPhase(
                phase_id=str(phase_id) if phase_id is not None else None,
                phase_name=phase_name(phase_id),
                predictions_count=pred_counts[phase_id],
                zones=sorted(zones, key=lambda z: z.zone_name),
            )
        )

    observations_summary = []
    for phase_id in ordered_phase_ids:
        if phase_id not in obs_count:
            continue
        zones = []
        for (zone_phase_id, zone_id), (count, total) in obs_zone_agg.items():
            if zone_phase_id != phase_id:
                continue
            zones.append(
                ZoneObservationSummary(
                    zone_id=zone_id,
                    zone_name=zone_by_id.get(zone_id, zone_id),
                    observations_count=count,
                    observed_density_total=total,
                    observed_density_avg=round(total / count, 2) if count else None,
                )
            )
        observations_summary.append(
            ObservationsPhase(
                phase_id=str(phase_id) if phase_id is not None else None,
                phase_name=phase_name(phase_id),
                observations_count=obs_count[phase_id],
                zones=sorted(zones, key=lambda z: z.zone_name),
            )
        )

    operational_events_summary = []
    for phase_id in ordered_phase_ids:
        if phase_id not in events_by_phase:
            continue
        phase_events = events_by_phase[phase_id]
        events = sorted(
            (
                OperationalEventSummaryItem(
                    operational_event_id=str(operational_event.id),
                    event_type=operational_event.event_type,
                    is_incident=operational_event.is_incident,
                    zone_id=operational_event.zone_id,
                    zone_name=zone_by_id.get(operational_event.zone_id),
                    start_timestamp=operational_event.start_timestamp,
                    end_timestamp=operational_event.end_timestamp,
                    description=operational_event.description,
                )
                for operational_event in phase_events
            ),
            key=lambda item: item.start_timestamp,
        )
        operational_events_summary.append(
            OperationalEventsPhase(
                phase_id=str(phase_id) if phase_id is not None else None,
                phase_name=phase_name(phase_id),
                total_events=len(events),
                incidents=incidents_by_phase.get(phase_id, 0),
                events=events,
            )
        )

    insufficient_data: list[str] = []
    if not event_days:
        insufficient_data.append(
            "El evento no tiene jornadas operativas (event_days) configuradas."
        )
    if not predictions:
        insufficient_data.append("No hay predicciones persistidas para las jornadas del evento.")
    if not observations:
        insufficient_data.append("No hay observaciones operativas para relacionar.")
    if not operational_events:
        insufficient_data.append("No hay eventos operativos registrados.")
    platform_unassigned = platform_totals.get(None)
    if platform_unassigned:
        insufficient_data.append(
            f"{platform_unassigned['consultas_total']} actividades de usuario sin fase asignada (fuera de ventana operativa)."
        )
    if obs_unassigned:
        insufficient_data.append(
            f"{obs_unassigned} observaciones sin fase asignada (fuera de ventana operativa)."
        )
    if events_unassigned:
        insufficient_data.append(
            f"{events_unassigned} eventos operativos sin fase asignada (fuera de ventana operativa)."
        )

    distinct_profiles = {ed.operational_profile_id for ed in event_days if ed.operational_profile_id}
    operational_profile_id = (
        next(iter(distinct_profiles)) if len(distinct_profiles) == 1 else None
    )

    return OperationalProfileResponse(
        event_id=event.id,
        event_name=event.name,
        period=PeriodRange(start=period.start, end=period.end, mode=period.mode),
        timezone=timezone,
        operational_profile_id=str(operational_profile_id) if operational_profile_id else None,
        phases=phases,
        platform_queries=platform_queries,
        predictions_summary=predictions_summary,
        observations_summary=observations_summary,
        operational_events_summary=operational_events_summary,
        insufficient_data=insufficient_data,
    )
