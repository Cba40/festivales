from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.event_state import EventState
from app.models.state_override import StateOverride
from tests.conftest import EVENT_STATE_IDS

pytestmark = pytest.mark.usefixtures("db_session")


class TestSmokeE2E:

    def test_full_flow(
        self,
        client: TestClient,
        db_session: Session,
        sample_event,
        sample_event_day,
        sample_zones,
    ):
        event_id = sample_event.id

        # ── 1. Login ────────────────────────────────
        login_resp = client.post("/api/auth/login", json={
            "username": "admin",
            "password": "1234",
        })
        assert login_resp.status_code == 200
        login_data = login_resp.json()
        assert "access_token" in login_data
        token = login_data["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # ── 2. Health check P2 ──────────────────────
        health_resp = client.get("/health/p2", headers=auth_headers)
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] in ("ok", "degraded")
        assert "checks" in health_data
        assert "timestamp" in health_data
        for table in ("event_states", "zone_types", "event_day_zone_factors", "state_overrides", "incident_impacts"):
            assert table in health_data["checks"]
        assert "columnas" in health_data["checks"]
        assert "seed_states" in health_data["checks"]
        assert "seed_zone_types" in health_data["checks"]

        # ── 3. GET /event-states ────────────────────
        states_resp = client.get("/api/context-engine/event-states", headers=auth_headers)
        assert states_resp.status_code == 200
        states = states_resp.json()
        assert len(states) >= 5
        slugs = [s["slug"] for s in states]
        for expected in ("pre_apertura", "temprano", "pico", "cierre", "post_evento"):
            assert expected in slugs

        # ── 4. GET /zone-types ──────────────────────
        zone_types_resp = client.get("/api/context-engine/zone-types", headers=auth_headers)
        assert zone_types_resp.status_code == 200
        zone_types = zone_types_resp.json()
        assert len(zone_types) >= 6

        # ── 5. GET /context-engine/state ────────────
        params = {"datetime_actual": "2026-07-10T11:00:00Z"}
        state_resp = client.get(
            f"/api/events/{event_id}/context-engine/state",
            params=params,
            headers=auth_headers,
        )
        assert state_resp.status_code == 200
        state_data = state_resp.json()
        assert state_data["estado_actual"] is not None
        assert "slug" in state_data["estado_actual"]
        assert state_data["override_activo"] is None

        # ── 6. GET /context-engine/predictions ──────
        pred_resp = client.get(
            f"/api/events/{event_id}/context-engine/predictions",
            params=params,
            headers=auth_headers,
        )
        assert pred_resp.status_code == 200
        pred_data = pred_resp.json()
        assert pred_data["estado_actual"] is not None
        assert "zonas" in pred_data
        assert len(pred_data["zonas"]) >= 1
        for zona in pred_data["zonas"]:
            assert "id" in zona
            assert "name" in zona
            assert "type" in zona
            assert "factores" in zona
            assert "prediccion" in zona

        # ── 7. POST /overrides ──────────────────────
        state_pico = db_session.get(EventState, EVENT_STATE_IDS["pico"])
        override_body = {
            "event_day_id": sample_event_day.id,
            "event_state_id": state_pico.id,
            "zone_type_id": None,
            "start_min": 480,
            "end_min": 1380,
            "reason": "Smoke test override",
            "created_by": "smoke_tester",
        }
        create_resp = client.post(
            f"/api/events/{event_id}/context-engine/overrides",
            json=override_body,
            headers=auth_headers,
        )
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["is_active"] is True
        override_id = created["id"]

        # ── 8. DELETE /overrides/{id} ───────────────
        delete_resp = client.delete(
            f"/api/events/{event_id}/context-engine/overrides/{override_id}",
            headers=auth_headers,
        )
        assert delete_resp.status_code == 200
        deleted = delete_resp.json()
        assert deleted["is_active"] is False
