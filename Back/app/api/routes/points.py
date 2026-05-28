# backend/app/api/routes/points.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.point import Point
from app.schemas.point import PointResponse
from app.api.deps import verify_token

router = APIRouter(prefix="/api/events/{event_id}/points", tags=["points"])


@router.get("", response_model=list[PointResponse])
def list_points(event_id: str, db: Session = Depends(get_db), _=Depends(verify_token)):
    points = db.query(Point).filter(Point.event_id == event_id).all()
    return points
