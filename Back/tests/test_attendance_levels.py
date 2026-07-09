from typing import Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud.attendance_level import attendance_level as crud
from app.models.attendance_level import AttendanceLevel
from app.models.event import Event
from app.schemas.attendance_level import AttendanceLevelCreate, AttendanceLevelUpdate

pytestmark = pytest.mark.usefixtures("db_session")


class TestAttendanceLevelCRUD:

    def test_create_valid_ranges(self, db_session: Session, sample_event: Event):
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000, global_multiplier=0.8), sample_event.id)
        crud.create(db_session, AttendanceLevelCreate(name="Media", min_people=5001, max_people=15000, global_multiplier=1.0), sample_event.id)
        crud.create(db_session, AttendanceLevelCreate(name="Alta", min_people=15001, max_people=30000, global_multiplier=1.3), sample_event.id)
        crud.create(db_session, AttendanceLevelCreate(name="Muy Alta", min_people=30001, max_people=60000, global_multiplier=1.6), sample_event.id)
        crud.create(db_session, AttendanceLevelCreate(name="Masiva", min_people=60001, max_people=None, global_multiplier=2.0), sample_event.id)

        levels = crud.get_by_event(db_session, sample_event.id)
        assert len(levels) == 5

    def test_create_overlapping_ranges_raises_422(self, db_session: Session, sample_event: Event):
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000, global_multiplier=0.8), sample_event.id)
        with pytest.raises(Exception) as exc:
            crud.create(db_session, AttendanceLevelCreate(name="Solapada", min_people=2500, max_people=8000, global_multiplier=1.0), sample_event.id)
        assert "422" in str(exc.value) or "solapados" in str(exc.value).lower()

    def test_create_ranges_with_gaps_raises_422(self, db_session: Session, sample_event: Event):
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000, global_multiplier=0.8), sample_event.id)
        with pytest.raises(Exception) as exc:
            crud.create(db_session, AttendanceLevelCreate(name="ConHueco", min_people=7000, max_people=15000, global_multiplier=1.0), sample_event.id)
        assert "422" in str(exc.value) or "hueco" in str(exc.value).lower()

    def test_create_multiple_null_max_people_raises_422(self, db_session: Session, sample_event: Event):
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000, global_multiplier=0.8), sample_event.id)
        crud.create(db_session, AttendanceLevelCreate(name="Masiva1", min_people=5001, max_people=None, global_multiplier=2.0), sample_event.id)
        with pytest.raises(Exception) as exc:
            crud.create(db_session, AttendanceLevelCreate(name="Masiva2", min_people=5001, max_people=None, global_multiplier=2.0), sample_event.id)
        assert "422" in str(exc.value)

    def test_update_range_validation(self, db_session: Session, sample_event: Event):
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000, global_multiplier=0.8), sample_event.id)
        media = crud.create(db_session, AttendanceLevelCreate(name="Media", min_people=5001, max_people=15000, global_multiplier=1.0), sample_event.id)
        crud.create(db_session, AttendanceLevelCreate(name="Masiva", min_people=15001, max_people=None, global_multiplier=2.0), sample_event.id)

        with pytest.raises(Exception) as exc:
            crud.update(db_session, media, AttendanceLevelUpdate(max_people=20000))
        assert "422" in str(exc.value) or "hueco" in str(exc.value).lower()

    def test_delete_level(self, db_session: Session, sample_event: Event):
        level = crud.create(db_session, AttendanceLevelCreate(name="Unico", min_people=0, max_people=None, global_multiplier=1.0), sample_event.id)
        crud.delete(db_session, level.id)
        assert crud.get(db_session, level.id) is None


class TestAttendanceLevelRoutes:

    def test_create_attendance_level_endpoint(
        self, client: TestClient, sample_event: Event, auth_headers: dict
    ):
        body = {
            "name": "Baja",
            "min_people": 0,
            "max_people": 5000,
            "global_multiplier": 0.8,
        }
        response = client.post(
            f"/api/events/{sample_event.id}/attendance-levels",
            json=body,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Baja"
        assert data["min_people"] == 0
        assert data["max_people"] == 5000
        assert data["global_multiplier"] == 0.8

    def test_create_overlapping_returns_422(
        self, client: TestClient, sample_event: Event, auth_headers: dict, db_session: Session
    ):
        from app.crud.attendance_level import attendance_level as crud
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000, global_multiplier=0.8), sample_event.id)

        body = {
            "name": "Solapada",
            "min_people": 2500,
            "max_people": 8000,
            "global_multiplier": 1.0,
        }
        response = client.post(
            f"/api/events/{sample_event.id}/attendance-levels",
            json=body,
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_list_attendance_levels(
        self, client: TestClient, sample_event: Event, auth_headers: dict, db_session: Session
    ):
        from app.crud.attendance_level import attendance_level as crud
        crud.create(db_session, AttendanceLevelCreate(name="Baja", min_people=0, max_people=5000, global_multiplier=0.8), sample_event.id)
        crud.create(db_session, AttendanceLevelCreate(name="Masiva", min_people=5001, max_people=None, global_multiplier=2.0), sample_event.id)

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
        from app.crud.attendance_level import attendance_level as crud
        level = crud.create(db_session, AttendanceLevelCreate(name="Unico", min_people=0, max_people=None, global_multiplier=1.0), sample_event.id)

        response = client.delete(
            f"/api/events/{sample_event.id}/attendance-levels/{level.id}",
            headers=auth_headers,
        )
        assert response.status_code == 204
