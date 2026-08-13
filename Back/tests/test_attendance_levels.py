from datetime import date

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.attendance_level import attendance_level as crud
from app.models.event import Event
from app.models.event_day import EventDay
from app.schemas.attendance_level import AttendanceLevelCreate, AttendanceLevelUpdate

pytestmark = pytest.mark.usefixtures("db_session")


def _make_day(
    db: Session,
    event_id: str,
    day_id: str,
    day_date: date,
    attendance_level_id: str,
) -> EventDay:
    day = EventDay(
        id=day_id,
        event_id=event_id,
        date=day_date,
        day_of_week=day_date.strftime("%A").lower(),
        is_active=True,
        operational_start_min=480,
        operational_end_min=1200,
        attendance_level_id=attendance_level_id,
    )
    db.add(day)
    db.flush()
    return day


class TestAttendanceLevelCRUD:

    def test_create_attendance_level_for_event(self, db_session: Session, sample_event: Event):
        level = crud.create(
            db_session,
            AttendanceLevelCreate(name="Asistencia Viernes", min_people=8000, max_people=12000),
            sample_event.id,
        )
        assert level.event_id == sample_event.id
        assert level.min_people == 8000
        assert level.max_people == 12000

    def test_create_for_another_event_succeeds(self, db_session: Session):
        other = Event(id="other-event", name="Otro", description="")
        db_session.add(other)
        db_session.flush()
        level = crud.create(
            db_session,
            AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000),
            other.id,
        )
        assert level.event_id == other.id

    def test_overlapping_ranges_allowed_same_event(self, db_session: Session, sample_event: Event):
        crud.create(db_session, AttendanceLevelCreate(name="Viernes", min_people=8000, max_people=12000), sample_event.id)
        crud.create(db_session, AttendanceLevelCreate(name="Sabado", min_people=10000, max_people=20000), sample_event.id)
        levels = crud.get_by_event(db_session, sample_event.id)
        assert len(levels) == 2

    def test_equal_ranges_allowed_same_event(self, db_session: Session, sample_event: Event):
        first = crud.create(db_session, AttendanceLevelCreate(name="A", min_people=8000, max_people=12000), sample_event.id)
        second = crud.create(db_session, AttendanceLevelCreate(name="B", min_people=8000, max_people=12000), sample_event.id)
        levels = crud.get_by_event(db_session, sample_event.id)
        assert len(levels) == 2
        assert first.id != second.id

    def test_same_level_reused_by_two_days(self, db_session: Session, sample_event: Event):
        level = crud.create(db_session, AttendanceLevelCreate(name="Unico", min_people=8000, max_people=12000), sample_event.id)
        day_a = _make_day(db_session, sample_event.id, "day-a", date(2026, 7, 10), level.id)
        day_b = _make_day(db_session, sample_event.id, "day-b", date(2026, 7, 11), level.id)
        assert day_a.attendance_level_id == level.id
        assert day_b.attendance_level_id == level.id

    def test_different_levels_two_days(self, db_session: Session, sample_event: Event):
        fri = crud.create(db_session, AttendanceLevelCreate(name="Viernes", min_people=8000, max_people=12000), sample_event.id)
        sat = crud.create(db_session, AttendanceLevelCreate(name="Sabado", min_people=20000, max_people=30000), sample_event.id)
        day_a = _make_day(db_session, sample_event.id, "day-a", date(2026, 7, 10), fri.id)
        day_b = _make_day(db_session, sample_event.id, "day-b", date(2026, 7, 11), sat.id)
        assert day_a.attendance_level_id == fri.id
        assert day_b.attendance_level_id == sat.id

    def test_update_level(self, db_session: Session, sample_event: Event):
        level = crud.create(db_session, AttendanceLevelCreate(name="Viernes", min_people=8000, max_people=12000), sample_event.id)
        updated = crud.update(
            db_session,
            level,
            AttendanceLevelUpdate(name="Viernes Actualizado", min_people=9000, max_people=15000),
            event_id=sample_event.id,
        )
        assert updated.name == "Viernes Actualizado"
        assert updated.min_people == 9000
        assert updated.max_people == 15000

    def test_invalid_range_rejected(self, db_session: Session, sample_event: Event):
        with pytest.raises(HTTPException) as exc:
            crud.create(db_session, AttendanceLevelCreate(name="Invalido", min_people=100, max_people=50), sample_event.id)
        assert exc.value.status_code == 422

    def test_negative_min_rejected(self, db_session: Session, sample_event: Event):
        with pytest.raises(HTTPException) as exc:
            crud.create(db_session, AttendanceLevelCreate(name="Invalido", min_people=-1, max_people=50), sample_event.id)
        assert exc.value.status_code == 422

    def test_delete_level_unused(self, db_session: Session, sample_event: Event):
        level = crud.create(db_session, AttendanceLevelCreate(name="Unico", min_people=0, max_people=None), sample_event.id)
        crud.delete(db_session, level.id)
        assert crud.get(db_session, level.id) is None

    def test_delete_level_in_use_raises_conflict(self, db_session: Session, sample_event: Event):
        level = crud.create(db_session, AttendanceLevelCreate(name="EnUso", min_people=0, max_people=5000), sample_event.id)
        _make_day(db_session, sample_event.id, "day-in-use", date(2026, 7, 10), level.id)
        with pytest.raises(HTTPException) as exc:
            crud.delete(db_session, level.id)
        assert exc.value.status_code == 409


class TestAttendanceLevelRoutes:

    def test_create_attendance_level_endpoint(
        self, client: TestClient, sample_event: Event, auth_headers: dict
    ):
        body = {
            "name": "Baja",
            "min_people": 0,
            "max_people": 5000,
        }
        response = client.post(
            f"/api/events/{sample_event.id}/attendance-levels",
            json=body,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["event_id"] == sample_event.id
        assert data["name"] == "Baja"
        assert data["min_people"] == 0
        assert data["max_people"] == 5000

    def test_create_overlapping_allowed(
        self, client: TestClient, sample_event: Event, auth_headers: dict, db_session: Session
    ):
        crud.create(db_session, AttendanceLevelCreate(name="Viernes", min_people=8000, max_people=12000), sample_event.id)
        body = {
            "name": "Sabado",
            "min_people": 10000,
            "max_people": 20000,
        }
        response = client.post(
            f"/api/events/{sample_event.id}/attendance-levels",
            json=body,
            headers=auth_headers,
        )
        assert response.status_code == 201

    def test_list_attendance_levels(
        self, client: TestClient, sample_event: Event, auth_headers: dict, db_session: Session
    ):
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000), sample_event.id)
        crud.create(db_session, AttendanceLevelCreate(name="Masiva", min_people=5001, max_people=None), sample_event.id)

        response = client.get(
            f"/api/events/{sample_event.id}/attendance-levels",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_delete_attendance_level(
        self, client: TestClient, sample_event: Event, auth_headers: dict, db_session: Session
    ):
        level = crud.create(db_session, AttendanceLevelCreate(name="Unico", min_people=0, max_people=None), sample_event.id)

        response = client.delete(
            f"/api/events/{sample_event.id}/attendance-levels/{level.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204

    def test_delete_level_in_use_returns_409(
        self, client: TestClient, sample_event: Event, auth_headers: dict, db_session: Session
    ):
        level = crud.create(db_session, AttendanceLevelCreate(name="EnUso", min_people=0, max_people=5000), sample_event.id)
        _make_day(db_session, sample_event.id, "day-in-use", date(2026, 7, 10), level.id)

        response = client.delete(
            f"/api/events/{sample_event.id}/attendance-levels/{level.id}",
            headers=auth_headers,
        )
        assert response.status_code == 409
