import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings, parse_cors_origins
from app.api.routes.auth import router as auth_router
from app.api.routes.events import router as events_router
from app.api.routes.zones import router as zones_router
from app.api.routes.points import router as points_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.event_days import router as event_days_router
from app.api.routes.attendance_levels import router as attendance_levels_router
from app.api.routes.catalogs import router as catalogs_router
from app.api.routes.health import router as health_router
from app.api.routes.operational_profiles import router as operational_profiles_router
from app.api.routes.operational_phases import router as operational_phases_router
from app.api.routes.zone_behaviors import router as zone_behaviors_router
from app.api.routes.operational_events import router as operational_events_router
from app.api.routes.operational_event_modifiers import router as operational_event_modifiers_router
from app.api.routes.predictions import router as predictions_router
from app.api.routes.recommendations import router as recommendations_router

app = FastAPI(title="Territorial MVP", version="0.1.0")

cors_origins = parse_cors_origins(os.environ.get("CORS_ORIGINS"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(events_router)
app.include_router(zones_router)
app.include_router(points_router)
app.include_router(incidents_router)
app.include_router(event_days_router)
app.include_router(attendance_levels_router)
app.include_router(catalogs_router)
app.include_router(health_router)
app.include_router(operational_profiles_router, prefix="/api")
app.include_router(operational_phases_router, prefix="/api")
app.include_router(zone_behaviors_router, prefix="/api")
app.include_router(operational_events_router, prefix="/api")
app.include_router(operational_event_modifiers_router, prefix="/api")
app.include_router(predictions_router)
app.include_router(recommendations_router)


@app.get("/health")
def health():
    return {"status": "ok"}
