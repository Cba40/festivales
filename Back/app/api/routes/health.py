import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import verify_token
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

P3_TABLES = [
    "operational_profiles",
    "event_days",
]


@router.get("/health/p3")
def health_p3(
    db: Session = Depends(get_db),
    _=Depends(verify_token),
):
    checks = {}

    table_ok = True
    for table in P3_TABLES:
        result = db.execute(
            text("SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = :t"),
            {"t": table},
        ).scalar()
        checks[table] = bool(result)
        if not result:
            table_ok = False

    profile_count = db.execute(text("SELECT COUNT(*) FROM operational_profiles")).scalar() or 0
    event_day_count = db.execute(text("SELECT COUNT(*) FROM event_days")).scalar() or 0
    checks["operational_profiles"] = profile_count
    checks["event_days"] = event_day_count

    status = "ok" if table_ok else "degraded"

    if status == "degraded":
        logger.warning(
            "Health check P3 degraded: tables=%s profiles=%s event_days=%s",
            table_ok, profile_count, event_day_count,
        )

    return {
        "status": status,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
