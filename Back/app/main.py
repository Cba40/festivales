# backend/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes.auth import router as auth_router
from app.api.routes.events import router as events_router
from app.api.routes.zones import router as zones_router
from app.api.routes.points import router as points_router
from app.api.routes.incidents import router as incidents_router

app = FastAPI(title="Territorial MVP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(events_router)
app.include_router(zones_router)
app.include_router(points_router)
app.include_router(incidents_router)


@app.get("/health")
def health():
    return {"status": "ok"}
