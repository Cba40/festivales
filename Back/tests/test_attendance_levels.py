import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.attendance_level import attendance_level as crud
from app.models.event import Event
from app.models.event_day import EventDay
from app.schemas.attendance_level import AttendanceLevelCreate, AttendanceLevelUpdate

pytestmark = pytest.mark.usefixtures("db_session")


class TestAttendanceLevelCRUD:

    def test_same_event_day_consecutive_ranges_valid(self, db_session: Session, sample_event: Event, sample_event_day: EventDay):
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=4999), sample_event_day.id)
        crud.create(db_session, AttendanceLevelCreate(name="Media", min_people=5000, max_people=10000), sample_event_day.id)
        levels = crud.get_by_event_day(db_session, sample_event_day.id)
        assert len(levels) == 2

    def test_same_event_day_overlapping_range_raises_422(self, db_session: Session, sample_event: Event, sample_event_day: EventDay):
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000), sample_event_day.id)
        with pytest.raises(Exception) as exc:
            crud.create(db_session, AttendanceLevelCreate(name="Solapada", min_people=5000, max_people=8000), sample_event_day.id)
        assert "422" in str(exc.value) or "solapados" in str(exc.value).lower()

    def test_different_event_days_same_ranges_valid(self, db_session: Session, sample_event: Event, sample_event_day: EventDay):
        other_day = EventDay(id="test-day-2", event_id=sample_event.id, date="2026-07-11", day_of_week="sabado", is_active=True)
        db_session.add(other_day)
        db_session.flush()

        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000), sample_event_day.id)
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000), other_day.id)
        levels = crud.get_by_event_day(db_session, sample_event_day.id)
        assert len(levels) == 1

    def test_different_event_days_similar_ranges_valid(self, db_session: Session, sample_event: Event, sample_event_day: EventDay):
        other_day = EventDay(id="test-day-3", event_id=sample_event.id, date="2026-07-12", day_of_week="domingo", is_active=True)
        db_session.add(other_day)
        db_session.flush()

        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=1000, max_people=5000), sample_event_day.id)
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=1000, max_people=5000), other_day.id)
        assert len(crud.get_by_event_day(db_session, sample_event_day.id)) == 1
        assert len(crud.get_by_event_day(db_session, other_day.id)) == 1

    def test_range_contained_in_another_raises_422(self, db_session: Session, sample_event: Event, sample_event_day: EventDay):
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=1000, max_people=10000), sample_event_day.id)
        with pytest.raises(Exception) as exc:
            crud.create(db_session, AttendanceLevelCreate(name="Media", min_people=3000, max_people=5000), sample_event_day.id)
        assert "422" in str(exc.value) or "solapados" in str(exc.value).lower()

    def test_select_attendance_level_by_range(self, db_session: Session, sample_event: Event, sample_event_day: EventDay):
        level = crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=1000, max_people=5000), sample_event_day.id)
        levels = crud.get_by_event_day(db_session, sample_event_day.id)
        match = [item for item in levels if item.min_people <= 2500 <= item.max_people]
        assert len(match) == 1
        assert match[0].id == level.id

    def test_attendance_out_of_ranges_returns_none(self, db_session: Session, sample_event: Event, sample_event_day: EventDay):
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=1000, max_people=5000), sample_event_day.id)
        levels = crud.get_by_event_day(db_session, sample_event_day.id)
        match = [item for item in levels if item.min_people <= 6000 <= item.max_people]
        assert match == []

    def test_event_day_belongs_to_other_event_rejected(self, db_session: Session, sample_event: Event, sample_event_day: EventDay):
        other_event = Event(id="other-event", name="Otro", description="")
        db_session.add(other_event)
        db_session.flush()
        other_day = EventDay(id="other-day", event_id=other_event.id, date="2026-07-11", day_of_week="sabado", is_active=True)
        db_session.add(other_day)
        db_session.flush()

        with pytest.raises(Exception):
            crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000), other_day.id)

    def test_event_day_resolved_by_date_and_event_id(self, db_session: Session, sample_event: Event):
        day = EventDay(id="date-event-day", event_id=sample_event.id, date="2026-07-15", day_of_week="viernes", is_active=True)
        db_session.add(day)
        db_session.flush()

        result = db_session.query(EventDay).filter(EventDay.event_id == sample_event.id, EventDay.date == "2026-07-15").first()
        assert result is not None
        assert result.id == day.id

    def test_delete_level(self, db_session: Session, sample_event: Event, sample_event_day: EventDay):
        level = crud.create(db_session, AttendanceLevelCreate(name="Unico", min_people=0, max_people=None), sample_event_day.id)
        crud.delete(db_session, level.id)
        assert crud.get(db_session, level.id) is None


class TestAttendanceLevelRoutes:

    def test_create_attendance_level_endpoint(
        self, client: TestClient, sample_event: Event, sample_event_day: EventDay, auth_headers: dict
    ):
        body = {
            "name": "Baja",
            "min_people": 0,
            "max_people": 5000,
        }
        response = client.post(
            f"/api/events/{sample_event.id}/days/{sample_event_day.id}/attendance-levels",
            json=body,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Baja"
        assert data["min_people"] == 0
        assert data["max_people"] == 5000

    def test_create_overlapping_returns_422(
        self, client: TestClient, sample_event: Event, sample_event_day: EventDay, auth_headers: dict, db_session: Session
    ):
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000), sample_event_day.id)

        body = {
            "name": "Solapada",
            "min_people": 2500,
            "max_people": 8000,
        }
        response = client.post(
            f"/api/events/{sample_event.id}/days/{sample_event_day.id}/attendance-levels",
            json=body,
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_list_attendance_levels(
        self, client: TestClient, sample_event: Event, sample_event_day: EventDay, auth_headers: dict, db_session: Session
    ):
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000), sample_event_day.id)
        crud.create(db_session, AttendanceLevelCreate(name="Masiva", min_people=5001, max_people=None), sample_event_day.id)

        response = client.get(
            f"/api/events/{sample_event.id}/days/{sample_event_day.id}/attendance-levels",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_delete_attendance_level(
        self, client: TestClient, sample_event: Event, sample_event_day: EventDay, auth_headers: dict, db_session: Session
    ):
        level = crud.create(db_session, AttendanceLevelCreate(name="Unico", min_people=0, max_people=None), sample_event_day.id)

        response = client.delete(
            f"/api/events/{sample_event.id}/days/{sample_event_day.id}/attendance-levels/{level.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
