from datetime import datetime, timezone
from typing import Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.event_day import EventDay
from app.models.event_state import EventState
from app.models.state_override import StateOverride
from app.models.zone import Zone
from app.models.zone_type import ZoneType
from tests.conftest import EVENT_STATE_IDS, ZONE_TYPE_IDS

pytestmark = pytest.mark.usefixtures("db_session")


class TestGetStateEndpoint:

    def test_get_state_endpoint(
        self, client: TestClient, sample_event: Event, sample_event_day: EventDay, auth_headers: dict
    ):
        params = {"datetime_actual": "2026-07-10T11:00:00Z"}
        response = client.get(
            f"/api/events/{sample_event.id}/context-engine/state",
            params=params,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estado_actual"] is not None
        assert data["estado_actual"]["slug"] == "pico"
        assert data["override_activo"] is None

    def test_get_state_endpoint_sin_jornada(
        self, client: TestClient, sample_event: Event, auth_headers: dict
    ):
        params = {"datetime_actual": "2026-07-11T12:00:00Z"}
        response = client.get(
            f"/api/events/{sample_event.id}/context-engine/state",
            params=params,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estado_actual"] is None
        assert data["override_activo"] is None


class TestGetPredictionsEndpoint:

    def test_get_predictions_endpoint(
        self,
        client: TestClient,
        sample_event: Event,
        sample_event_day: EventDay,
        sample_zones: list[Zone],
        auth_headers: dict,
    ):
        params = {"datetime_actual": "2026-07-10T11:00:00Z"}
        response = client.get(
            f"/api/events/{sample_event.id}/context-engine/predictions",
            params=params,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["estado_actual"] is not None
        assert data["estado_actual"]["slug"] == "pico"
        assert data["override_activo"] is None
        assert len(data["zonas"]) == 3
        for zona in data["zonas"]:
            assert "id" in zona
            assert "name" in zona
            assert "type" in zona
            assert "factores" in zona
            assert "prediccion" in zona


class TestCreateOverrideEndpoint:

    def test_create_override_endpoint(
        self,
        client: TestClient,
        sample_event: Event,
        sample_event_day: EventDay,
        auth_headers: dict,
        db_session: Session,
    ):
        state_pico = db_session.get(EventState, EVENT_STATE_IDS["pico"])
        body = {
            "event_day_id": sample_event_day.id,
            "event_state_id": state_pico.id,
            "zone_type_id": None,
            "start_min": 0,
            "end_min": 900,
            "reason": "Prueba de override",
            "created_by": "tester",
        }
        response = client.post(
            f"/api/events/{sample_event.id}/context-engine/overrides",
            json=body,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["event_day_id"] == sample_event_day.id
        assert data["event_state_id"] == state_pico.id
        assert data["is_active"] is True
        assert "id" in data


class TestCancelOverrideEndpoint:

    def test_cancel_override_endpoint(
        self,
        client: TestClient,
        sample_event: Event,
        sample_event_day: EventDay,
        auth_headers: dict,
        db_session: Session,
    ):
        state_pico = db_session.get(EventState, EVENT_STATE_IDS["pico"])
        override = StateOverride(
            id="override-cancel-1",
            event_day_id=sample_event_day.id,
            event_state_id=state_pico.id,
            zone_type_id=None,
            start_min=0,
            end_min=900,
            reason="To be cancelled",
            created_by="tester",
            is_active=True,
        )
        db_session.add(override)
        db_session.flush()

        response = client.delete(
            f"/api/events/{sample_event.id}/context-engine/overrides/{override.id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False


class TestCrudEventDayZoneFactors:

    def test_crud_event_day_zone_factors(
        self,
        client: TestClient,
        sample_event: Event,
        sample_event_day: EventDay,
        auth_headers: dict,
        db_session: Session,
    ):
        state_temprano = db_session.get(EventState, EVENT_STATE_IDS["temprano"])
        zt_comida = db_session.get(ZoneType, ZONE_TYPE_IDS["puesto_comida"])

        body = {
            "event_day_id": sample_event_day.id,
            "zone_type_id": zt_comida.id,
            "event_state_id": state_temprano.id,
            "saturation_factor": 0.8,
            "attendance_factor": 1.1,
            "resource_factor": 0.9,
            "priority_weight": 60,
        }
        response = client.post(
            f"/api/events/{sample_event.id}/context-engine/event-day-zone-factors",
            json=body,
            headers=auth_headers,
        )
        assert response.status_code == 201
        created = response.json()
        factor_id = created["id"]
        assert created["saturation_factor"] == 0.8

        update_body = {
            "saturation_factor": 1.5,
            "attendance_factor": 1.8,
        }
        response = client.put(
            f"/api/events/{sample_event.id}/context-engine/event-day-zone-factors/{factor_id}",
            json=update_body,
            headers=auth_headers,
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["saturation_factor"] == 1.5
        assert updated["attendance_factor"] == 1.8

        response = client.delete(
            f"/api/events/{sample_event.id}/context-engine/event-day-zone-factors/{factor_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        deleted = response.json()
        assert deleted["id"] == factor_id


class TestEndpointsRequierenAuth:

    def _assert_401(self, response):
        assert response.status_code == 401

    def test_get_state_sin_auth(self, client: TestClient, sample_event: Event):
        response = client.get(f"/api/events/{sample_event.id}/context-engine/state")
        self._assert_401(response)

    def test_get_predictions_sin_auth(self, client: TestClient, sample_event: Event):
        response = client.get(f"/api/events/{sample_event.id}/context-engine/predictions")
        self._assert_401(response)

    def test_create_override_sin_auth(self, client: TestClient, sample_event: Event, sample_event_day: EventDay):
        body = {
            "event_day_id": sample_event_day.id,
            "event_state_id": "any-id",
            "start_min": 0,
            "end_min": 900,
            "reason": "test",
            "created_by": "tester",
        }
        response = client.post(
            f"/api/events/{sample_event.id}/context-engine/overrides",
            json=body,
        )
        self._assert_401(response)

    def test_cancel_override_sin_auth(self, client: TestClient, sample_event: Event):
        response = client.delete(f"/api/events/{sample_event.id}/context-engine/overrides/some-id")
        self._assert_401(response)

    def test_create_factor_sin_auth(self, client: TestClient, sample_event: Event):
        response = client.post(
            f"/api/events/{sample_event.id}/context-engine/event-day-zone-factors",
            json={},
        )
        self._assert_401(response)
