from datetime import date, datetime, timezone
from typing import Optional

import pytest
from sqlalchemy.orm import Session

from app.models.event_day import EventDay
from app.models.event_day_zone_factor import EventDayZoneFactor
from app.models.event_state import EventState
from app.models.incident import Incident
from app.models.incident_impact import IncidentImpact
from app.models.state_override import StateOverride
from app.models.zone import Zone
from app.models.zone_type import ZoneType
from app.services import context_engine
from app.services.context_engine import SEVERITY_WEIGHTS
from tests.conftest import EVENT_STATE_IDS, ZONE_TYPE_IDS

pytestmark = pytest.mark.usefixtures("db_session")


class TestGetCurrentState:

    def test_get_current_state_sin_jornada_activa(self, db_session: Session, sample_event):
        dt = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        state, override = context_engine.get_current_state(db_session, sample_event.id, dt)
        assert state is None
        assert override is None

    def test_get_current_state_con_override_global(
        self, db_session: Session, sample_event, sample_event_day
    ):
        state_pico = db_session.get(EventState, EVENT_STATE_IDS["pico"])
        override = StateOverride(
            id="override-global-1",
            event_day_id=sample_event_day.id,
            event_state_id=state_pico.id,
            zone_type_id=None,
            start_min=0,
            end_min=900,
            reason="Test global override",
            created_by="tester",
            is_active=True,
        )
        db_session.add(override)
        db_session.flush()

        dt = datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)
        state, active_override = context_engine.get_current_state(db_session, sample_event.id, dt)
        assert state is not None
        assert state.slug == "pico"
        assert active_override is not None
        assert active_override.id == "override-global-1"

    def test_get_current_state_con_override_especifico(
        self, db_session: Session, sample_event, sample_event_day
    ):
        state_pico = db_session.get(EventState, EVENT_STATE_IDS["pico"])
        zt_puesto = db_session.get(ZoneType, ZONE_TYPE_IDS["puesto_comida"])
        override = StateOverride(
            id="override-specific-1",
            event_day_id=sample_event_day.id,
            event_state_id=state_pico.id,
            zone_type_id=zt_puesto.id,
            start_min=0,
            end_min=900,
            reason="Test specific override",
            created_by="tester",
            is_active=True,
        )
        db_session.add(override)
        db_session.flush()

        dt = datetime(2026, 7, 10, 9, 0, tzinfo=timezone.utc)
        state, active_override = context_engine.get_current_state(db_session, sample_event.id, dt)
        assert state is not None
        assert state.slug == "pre_apertura"
        assert active_override is None

    def test_get_current_state_regla_minutos_pre_apertura(
        self, db_session: Session, sample_event, sample_event_day
    ):
        dt = datetime(2026, 7, 10, 7, 59, tzinfo=timezone.utc)
        state, _ = context_engine.get_current_state(db_session, sample_event.id, dt)
        assert state is None

    def test_get_current_state_regla_minutos_temprano(
        self, db_session: Session, sample_event, sample_event_day
    ):
        dt = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
        state, _ = context_engine.get_current_state(db_session, sample_event.id, dt)
        assert state is not None
        assert state.slug == "temprano"

    def test_get_current_state_regla_minutos_pico(
        self, db_session: Session, sample_event, sample_event_day
    ):
        dt = datetime(2026, 7, 10, 13, 0, tzinfo=timezone.utc)
        state, _ = context_engine.get_current_state(db_session, sample_event.id, dt)
        assert state is not None
        assert state.slug == "pico"

    def test_get_current_state_regla_minutos_cierre(
        self, db_session: Session, sample_event, sample_event_day
    ):
        dt = datetime(2026, 7, 10, 20, 0, tzinfo=timezone.utc)
        state, _ = context_engine.get_current_state(db_session, sample_event.id, dt)
        assert state is not None
        assert state.slug == "cierre"

    def test_get_current_state_regla_minutos_post_evento(
        self, db_session: Session, sample_event, sample_event_day
    ):
        dt = datetime(2026, 7, 10, 23, 0, tzinfo=timezone.utc)
        state, _ = context_engine.get_current_state(db_session, sample_event.id, dt)
        assert state is not None
        assert state.slug == "post_evento"

    def test_get_current_state_cruce_medianoche(
        self, db_session: Session, sample_event, sample_event_day_cross_midnight
    ):
        dt = datetime(2026, 7, 11, 2, 0, tzinfo=timezone.utc)
        state, _ = context_engine.get_current_state(db_session, sample_event.id, dt)
        assert state is not None

    def test_get_current_state_override_evaluado_con_minutos(
        self, db_session: Session, sample_event, sample_event_day
    ):
        state_pico = db_session.get(EventState, EVENT_STATE_IDS["pico"])
        override = StateOverride(
            id="override-min-1",
            event_day_id=sample_event_day.id,
            event_state_id=state_pico.id,
            zone_type_id=None,
            start_min=120,
            end_min=720,
            reason="Override de 10:00 a 20:00",
            created_by="tester",
            is_active=True,
        )
        db_session.add(override)
        db_session.flush()

        dt = datetime(2026, 7, 10, 15, 0, tzinfo=timezone.utc)
        state, active_override = context_engine.get_current_state(db_session, sample_event.id, dt)
        assert state is not None
        assert state.slug == "pico"
        assert active_override is not None

        dt = datetime(2026, 7, 10, 21, 0, tzinfo=timezone.utc)
        state, _ = context_engine.get_current_state(db_session, sample_event.id, dt)
        assert state is not None
        assert state.slug == "cierre"


class TestComputePredictions:

    def test_compute_predictions_sin_jornada(self, db_session: Session, sample_event, sample_zones):
        dt = datetime(2026, 7, 11, 12, 0, tzinfo=timezone.utc)
        result = context_engine.compute_predictions(db_session, sample_event.id, dt)
        assert result["estado_actual"] is None
        assert result["override_activo"] is None
        assert len(result["zonas"]) == 3
        for z in result["zonas"]:
            assert z["factores"]["saturation"] == 1.0
            assert z["factores"]["attendance"] == 1.0
            assert z["factores"]["resource"] == 1.0

    def test_compute_predictions_con_factores_personalizados(
        self, db_session: Session, sample_event, sample_event_day, sample_zones
    ):
        zt = db_session.get(ZoneType, ZONE_TYPE_IDS["puesto_comida"])
        state_temprano = db_session.get(EventState, EVENT_STATE_IDS["temprano"])
        edzf = EventDayZoneFactor(
            id="edzf-custom-1",
            event_day_id=sample_event_day.id,
            zone_type_id=zt.id,
            event_state_id=state_temprano.id,
            saturation_factor=0.9,
            attendance_factor=1.2,
            resource_factor=0.8,
            priority_weight=75,
        )
        db_session.add(edzf)
        db_session.flush()

        dt = datetime(2026, 7, 10, 10, 15, tzinfo=timezone.utc)
        result = context_engine.compute_predictions(db_session, sample_event.id, dt)
        assert result["estado_actual"] is not None
        assert result["estado_actual"].slug == "temprano"

        zona_comida = next(z for z in result["zonas"] if z["id"] == "zone-comida-1")
        assert zona_comida["factores"]["saturation"] == 0.9
        assert zona_comida["factores"]["attendance"] == 1.2
        assert zona_comida["factores"]["resource"] == 0.8
        assert zona_comida["factores"]["priority"] == 75

    def test_compute_predictions_fallback_default_factors(
        self, db_session: Session, sample_event, sample_event_day, sample_zones
    ):
        dt = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
        result = context_engine.compute_predictions(db_session, sample_event.id, dt)

        zona_bano = next(z for z in result["zonas"] if z["id"] == "zone-bano-1")
        assert zona_bano["factores"]["saturation"] == 0.3
        assert zona_bano["factores"]["attendance"] == 0.4
        assert zona_bano["factores"]["resource"] == 0.7

    def test_compute_predictions_con_incidente_activo(
        self, db_session: Session, sample_event, sample_event_day, sample_zones
    ):
        zona_bano = db_session.get(Zone, "zone-bano-1")
        zt_bano = db_session.get(ZoneType, ZONE_TYPE_IDS["bano"])
        incident = Incident(
            id="inc-1",
            event_id=sample_event.id,
            type="averia",
            severity="alta",
            description="Baño fuera de servicio parcial",
            status="abierto",
            zone_id=zona_bano.id,
        )
        db_session.add(incident)
        db_session.flush()

        impact = IncidentImpact(
            id="impact-1",
            incident_id=incident.id,
            zone_type_id=zt_bano.id,
            saturation_delta=0.5,
            attendance_delta=-0.3,
            resource_delta=0.4,
        )
        db_session.add(impact)
        db_session.flush()

        dt = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
        result = context_engine.compute_predictions(db_session, sample_event.id, dt)

        zona_bano_result = next(z for z in result["zonas"] if z["id"] == "zone-bano-1")
        severity_weight = SEVERITY_WEIGHTS["alta"]
        expected_saturation = 0.3 + 0.5 * severity_weight
        expected_attendance = 0.4 + (-0.3) * severity_weight
        expected_resource = 0.7 + 0.4 * severity_weight

        assert abs(zona_bano_result["factores"]["saturation"] - expected_saturation) < 0.01
        assert abs(zona_bano_result["factores"]["attendance"] - expected_attendance) < 0.01
        assert abs(zona_bano_result["factores"]["resource"] - expected_resource) < 0.01

    def test_compute_predictions_incidente_sin_zona(
        self, db_session: Session, sample_event, sample_event_day, sample_zones
    ):
        zt_bano = db_session.get(ZoneType, ZONE_TYPE_IDS["bano"])
        incident = Incident(
            id="inc-nozone-1",
            event_id=sample_event.id,
            type="corte_agua",
            severity="media",
            description="Corte de agua general",
            status="abierto",
            zone_id=None,
        )
        db_session.add(incident)
        db_session.flush()

        impact = IncidentImpact(
            id="impact-nozone-1",
            incident_id=incident.id,
            zone_type_id=zt_bano.id,
            saturation_delta=0.2,
            attendance_delta=-0.1,
            resource_delta=0.3,
        )
        db_session.add(impact)
        db_session.flush()

        dt = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
        result = context_engine.compute_predictions(db_session, sample_event.id, dt)

        zona_bano = next(z for z in result["zonas"] if z["id"] == "zone-bano-1")
        severity_weight = SEVERITY_WEIGHTS["media"]
        expected_attendance = 0.4 + (-0.1) * severity_weight
        assert abs(zona_bano["factores"]["attendance"] - expected_attendance) < 0.01

    def test_compute_predictions_clamping(
        self, db_session: Session, sample_event, sample_event_day, sample_zones
    ):
        zt_comida = db_session.get(ZoneType, ZONE_TYPE_IDS["puesto_comida"])
        state_pico = db_session.get(EventState, EVENT_STATE_IDS["pico"])
        edzf = EventDayZoneFactor(
            id="edzf-clamp-1",
            event_day_id=sample_event_day.id,
            zone_type_id=zt_comida.id,
            event_state_id=state_pico.id,
            saturation_factor=5.0,
            attendance_factor=-1.0,
            resource_factor=3.0,
            priority_weight=150,
        )
        db_session.add(edzf)
        db_session.flush()

        dt = datetime(2026, 7, 10, 14, 0, tzinfo=timezone.utc)
        result = context_engine.compute_predictions(db_session, sample_event.id, dt)

        zona_comida = next(z for z in result["zonas"] if z["id"] == "zone-comida-1")
        assert zona_comida["factores"]["saturation"] == 2.0
        assert zona_comida["factores"]["attendance"] == 0.0
        assert zona_comida["factores"]["resource"] == 2.0

    def test_compute_predictions_con_attendance_level(
        self, db_session: Session, sample_event, sample_event_day, sample_zones, sample_attendance_levels
    ):
        dt = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
        result = context_engine.compute_predictions(db_session, sample_event.id, dt)

        zona_comida = next(z for z in result["zonas"] if z["id"] == "zone-comida-1")
        assert result["estado_actual"] is not None
        assert result["estado_actual"].slug == "temprano"
        assert abs(zona_comida["prediccion"]["attendance_predicha"] - 1.0 * 0.5 * 1.6) < 0.01

    def test_compute_predictions_attendance_level_fallback(
        self, db_session: Session, sample_event, sample_event_day, sample_zones
    ):
        dt = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
        result = context_engine.compute_predictions(db_session, sample_event.id, dt)

        zona_comida = next(z for z in result["zonas"] if z["id"] == "zone-comida-1")
        expected_attendance = 1.0 * 0.5 * 1.0
        assert abs(zona_comida["prediccion"]["attendance_predicha"] - expected_attendance) < 0.01

    def test_compute_predictions_attendance_level_limite_exacto(
        self, db_session: Session, sample_event, sample_event_day, sample_zones, sample_attendance_levels
    ):
        sample_event_day.estimated_attendance = 15000
        db_session.flush()

        dt = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
        result = context_engine.compute_predictions(db_session, sample_event.id, dt)

        zona_comida = next(z for z in result["zonas"] if z["id"] == "zone-comida-1")
        assert abs(zona_comida["prediccion"]["attendance_predicha"] - 1.0 * 0.5 * 1.0) < 0.01

    def test_compute_predictions_attendance_level_abierto(
        self, db_session: Session, sample_event, sample_event_day, sample_zones, sample_attendance_levels
    ):
        sample_event_day.estimated_attendance = 100000
        db_session.flush()

        dt = datetime(2026, 7, 10, 10, 0, tzinfo=timezone.utc)
        result = context_engine.compute_predictions(db_session, sample_event.id, dt)

        zona_comida = next(z for z in result["zonas"] if z["id"] == "zone-comida-1")
        assert abs(zona_comida["prediccion"]["attendance_predicha"] - 1.0 * 0.5 * 2.0) < 0.01


class TestEvaluateCompuestoRule:

    def test_evaluate_compuesto_rule_and(
        self, db_session: Session, sample_event, sample_event_day
    ):
        current_min = 180
        rule = {
            "tipo": "compuesto",
            "operador": "AND",
            "reglas": [
                {"tipo": "minutos", "campo_inicio": "activity_peak_start_min", "campo_fin": "exit_start_min"},
                {"tipo": "minutos", "campo_inicio": "entry_start_min", "campo_fin": "event_end_min"},
            ],
        }
        result = context_engine._evaluate_compuesto_rule(rule, sample_event_day, current_min)
        assert result is True

        current_min = -1
        result = context_engine._evaluate_compuesto_rule(rule, sample_event_day, current_min)
        assert result is False

    def test_evaluate_compuesto_rule_or(
        self, db_session: Session, sample_event, sample_event_day
    ):
        rule = {
            "tipo": "compuesto",
            "operador": "OR",
            "reglas": [
                {"tipo": "minutos", "campo_inicio": "activity_peak_end_min", "campo_fin": "exit_start_min"},
                {"tipo": "minutos", "campo_inicio": "activity_peak_start_min", "campo_fin": "activity_peak_end_min"},
            ],
        }
        current_min = 700
        result = context_engine._evaluate_compuesto_rule(rule, sample_event_day, current_min)
        assert result is True

        current_min = 0
        result = context_engine._evaluate_compuesto_rule(rule, sample_event_day, current_min)
        assert result is False
