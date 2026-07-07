import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import verify_token
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

P2_TABLES = [
    "event_states",
    "zone_types",
    "event_day_zone_factors",
    "state_overrides",
    "incident_impacts",
]

P2_TIME_COLUMNS = [
    "entry_start_time",
    "entry_peak_start_time",
    "entry_peak_end_time",
    "event_start_time",
    "exit_peak_start_time",
    "exit_peak_end_time",
    "event_end_time",
]


@router.get("/health/p2")
def health_p2(
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    checks = {}

    table_ok = True
    for table in P2_TABLES:
        result = db.execute(
            text("SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = :t"),
            {"t": table},
        ).scalar()
        checks[table] = bool(result)
        if not result:
            table_ok = False

    columns_ok = True
    column_check = True
    for col in P2_TIME_COLUMNS:
        result = db.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = 'event_days' AND column_name = :c"
            ),
            {"c": col},
        ).scalar()
        if not result:
            column_check = False
            columns_ok = False
    checks["columnas"] = column_check

    state_count = db.execute(text("SELECT COUNT(*) FROM event_states")).scalar() or 0
    zone_count = db.execute(text("SELECT COUNT(*) FROM zone_types")).scalar() or 0
    checks["seed_states"] = state_count
    checks["seed_zone_types"] = zone_count

    seed_ok = state_count >= 5 and zone_count >= 6

    status = "ok" if (table_ok and columns_ok and seed_ok) else "degraded"

    if status == "degraded":
        logger.warning(
            "Health check P2 degraded: tables=%s cols=%s states=%s zone_types=%s",
            table_ok, columns_ok, state_count, zone_count,
        )

    return {
        "status": status,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
