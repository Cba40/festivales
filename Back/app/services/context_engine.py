import logging
import time as time_module
from datetime import date, datetime, time, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crud.zone_type import zone_type as zone_type_crud
from app.crud.event_day_zone_factor import event_day_zone_factor as edzf_crud
from app.crud.state_override import state_override as state_override_crud
from app.models.event_day import EventDay
from app.models.event_state import EventState
from app.models.incident import Incident
from app.models.zone import Zone
from app.models.zone_type import ZoneType

logger = logging.getLogger(__name__)

SEVERITY_WEIGHTS = {
    "baja": 0.25,
    "media": 0.5,
    "alta": 0.75,
    "critica": 1.0,
}


def _clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(value, max_val))


class ContextEngineService:

    def get_current_state(self, db: Session, event_id: str, datetime_actual: Optional[datetime] = None) -> tuple[Optional[EventState], Optional[object]]:
        dt = datetime_actual if datetime_actual is not None else datetime.now(timezone.utc)
        event_day = self._get_active_event_day(db, event_id, dt.date())
        if not event_day:
            return None, None
        return self._resolve_state(db, event_id, event_day, dt)

    def compute_predictions(self, db: Session, event_id: str, datetime_actual: Optional[datetime] = None) -> dict:
        dt = datetime_actual if datetime_actual is not None else datetime.now(timezone.utc)
        _t0 = time_module.time()

        event_day = self._get_active_event_day(db, event_id, dt.date())
        t1 = time_module.time()
        logger.info("context_engine.step_1_get_event_day completed in %.3fs", t1 - _t0)
        if not event_day:
            logger.info("context_engine.completed no_event_day event_id=%s in %.3fs", event_id, time_module.time() - _t0)
            return self._baseline_response(event_id, db)

        current_state, override = self._resolve_state(db, event_id, event_day, dt)
        t2 = time_module.time()
        logger.info("context_engine.step_2_resolve_state completed in %.3fs", t2 - t1)
        if not current_state:
            logger.info("context_engine.completed no_state event_id=%s in %.3fs", event_id, time_module.time() - _t0)
            return self._baseline_response(event_id, db)

        zones = self._get_event_zones(db, event_id)
        t3 = time_module.time()
        logger.info("context_engine.step_3_get_zones completed in %.3fs (%d zones)", t3 - t2, len(zones))
        if not zones:
            logger.info("context_engine.completed no_zones event_id=%s in %.3fs", event_id, time_module.time() - _t0)
            return {
                "estado_actual": current_state,
                "override_activo": override,
                "zonas": [],
            }

        factors = self._calculate_base_factors(db, event_day.id, current_state.id, current_state.slug, zones)
        t4 = time_module.time()
        logger.info("context_engine.step_4_base_factors completed in %.3fs (%d zones)", t4 - t3, len(factors))
        logger.debug("context_engine.step_4_factors event_id=%s factors=%s", event_id, factors)

        factors = self._apply_incident_corrections(db, event_id, zones, factors)
        t5 = time_module.time()
        logger.info("context_engine.step_5_incident_corrections completed in %.3fs", t5 - t4)

        factors = self._apply_specific_overrides(db, event_day.id, dt, zones, factors)
        t6 = time_module.time()
        logger.info("context_engine.step_6_specific_overrides completed in %.3fs", t6 - t5)

        predictions = self._generate_predictions(zones, factors)
        t7 = time_module.time()
        logger.info(
            "context_engine.completed event_id=%s state=%s zones=%d total=%.3fs",
            event_id, current_state.slug, len(predictions), t7 - _t0,
        )

        return {
            "estado_actual": current_state,
            "override_activo": override,
            "zonas": predictions,
        }

    def _get_active_event_day(self, db: Session, event_id: str, target_date: date) -> Optional[EventDay]:
        stmt = select(EventDay).where(
            EventDay.event_id == event_id,
            EventDay.date == target_date,
            EventDay.is_active == True,
        )
        return db.execute(stmt).scalar_one_or_none()

    def _get_event_zones(self, db: Session, event_id: str) -> list[Zone]:
        stmt = select(Zone).where(Zone.event_id == event_id)
        return list(db.execute(stmt).scalars().all())

    def _resolve_state(self, db: Session, event_id: str, event_day: EventDay, dt: datetime) -> tuple[Optional[EventState], Optional[object]]:
        active_overrides = state_override_crud.get_active_overrides(db, event_day.id, dt)
        global_override = next((o for o in active_overrides if o.zone_type_id is None), None)
        if global_override:
            return global_override.event_state, global_override
        current_time = dt.time()
        state = self._evaluate_rules(db, event_id, event_day, current_time)
        return state, None

    def _evaluate_rules(self, db: Session, event_id: str, event_day: EventDay, current_time: time) -> Optional[EventState]:
        stmt = (
            select(EventState)
            .where((EventState.event_id == event_id) | (EventState.event_id == None))
            .order_by(EventState.sort_order)
        )
        states = list(db.execute(stmt).scalars().all())
        if not states:
            return None

        for state in states:
            if self._evaluate_rule(state.rules, event_day, current_time):
                return state

        return None

    def _evaluate_rule(self, rules: dict, event_day: EventDay, current_time: time) -> bool:
        rule_type = rules.get("tipo")
        if rule_type == "horario":
            return self._evaluate_horario_rule(rules, event_day, current_time)
        elif rule_type == "porcentaje_asistencia":
            return self._evaluate_porcentaje_asistencia_rule(rules, event_day)
        elif rule_type == "evento_externo":
            return False
        elif rule_type == "compuesto":
            return self._evaluate_compuesto_rule(rules, event_day, current_time)
        return False

    def _evaluate_horario_rule(self, rule: dict, event_day: EventDay, current_time: time) -> bool:
        campo_inicio_name = rule.get("campo_inicio")
        campo_fin_name = rule.get("campo_fin")

        if campo_inicio_name is not None:
            campo_inicio = getattr(event_day, campo_inicio_name, None)
            if campo_inicio is None:
                logger.warning("campo_inicio '%s' is None on EventDay %s", campo_inicio_name, event_day.id)
                return False
        else:
            campo_inicio = None

        if campo_fin_name is not None:
            campo_fin = getattr(event_day, campo_fin_name, None)
            if campo_fin is None:
                logger.warning("campo_fin '%s' is None on EventDay %s", campo_fin_name, event_day.id)
                return False
        else:
            campo_fin = None

        lower_ok = (campo_inicio is None or campo_inicio <= current_time)
        upper_ok = (campo_fin is None or current_time < campo_fin)

        return lower_ok and upper_ok

    def _evaluate_porcentaje_asistencia_rule(self, rule: dict, event_day: EventDay) -> bool:
        threshold = rule.get("threshold", 0.0)
        comparacion = rule.get("comparacion", ">=")
        expected = event_day.expected_attendance or 0
        if expected <= 0:
            return False
        ratio = 0.0
        if comparacion == ">=":
            return ratio >= threshold
        elif comparacion == ">":
            return ratio > threshold
        elif comparacion == "<=":
            return ratio <= threshold
        elif comparacion == "<":
            return ratio < threshold
        return False

    def _evaluate_compuesto_rule(self, rule: dict, event_day: EventDay, current_time: time) -> bool:
        operador = rule.get("operador", "AND")
        subreglas = rule.get("reglas", [])
        if not subreglas:
            return False
        results = [self._evaluate_rule(r, event_day, current_time) for r in subreglas]
        if operador == "AND":
            return all(results)
        elif operador == "OR":
            return any(results)
        logger.warning("Unknown compuesto operator '%s'", operador)
        return False

    def _calculate_base_factors(self, db: Session, event_day_id: str, state_id: str, state_slug: str, zones: list[Zone]) -> dict:
        zone_type_cache: dict[str, Optional[ZoneType]] = {}
        factors: dict[str, dict] = {}

        for zone in zones:
            if zone.type not in zone_type_cache:
                zone_type_cache[zone.type] = zone_type_crud.get_by_slug(db, zone.type)
            zt = zone_type_cache[zone.type]

            if zt is None:
                factors[zone.id] = {
                    "saturation": 1.0,
                    "attendance": 1.0,
                    "resource": 1.0,
                    "priority": 0,
                }
                continue

            edzf = edzf_crud.get_by_combo(db, event_day_id, zt.id, state_id)
            if edzf is not None:
                factors[zone.id] = {
                    "saturation": _clamp(edzf.saturation_factor, 0.0, 2.0),
                    "attendance": _clamp(edzf.attendance_factor, 0.0, 2.0),
                    "resource": _clamp(edzf.resource_factor, 0.0, 2.0),
                    "priority": _clamp(edzf.priority_weight, 0, 200),
                }
            else:
                defaults = zt.default_factors.get(state_slug, {})
                factors[zone.id] = {
                    "saturation": _clamp(defaults.get("saturation", 1.0), 0.0, 2.0),
                    "attendance": _clamp(defaults.get("attendance", 1.0), 0.0, 2.0),
                    "resource": _clamp(defaults.get("resource", 1.0), 0.0, 2.0),
                    "priority": int(_clamp(defaults.get("priority", 0), 0, 200)),
                }

        return factors

    def _apply_incident_corrections(self, db: Session, event_id: str, zones: list[Zone], factors: dict) -> dict:
        stmt = select(Incident).where(
            Incident.event_id == event_id,
            Incident.status.in_(["abierto", "en_curso"]),
        )
        active_incidents = list(db.execute(stmt).scalars().all())
        if not active_incidents:
            return factors

        zone_type_cache: dict[str, Optional[ZoneType]] = {}

        def _get_zt(zt_id: str) -> Optional[ZoneType]:
            if zt_id not in zone_type_cache:
                zone_type_cache[zt_id] = db.get(ZoneType, zt_id)
            return zone_type_cache[zt_id]

        for incident in active_incidents:
            severity_weight = SEVERITY_WEIGHTS.get(incident.severity, 0.5)
            impacts = list(incident.incident_impacts)

            for impact in impacts:
                zt = _get_zt(impact.zone_type_id)
                if not zt:
                    continue

                if incident.zone_id is not None:
                    target_zone = next((z for z in zones if z.id == incident.zone_id), None)
                    if target_zone and target_zone.type == zt.slug:
                        self._apply_delta(factors, target_zone.id, impact, severity_weight)
                else:
                    for zone in zones:
                        if zone.type == zt.slug:
                            self._apply_delta(factors, zone.id, impact, severity_weight)

        return factors

    def _apply_delta(self, factors: dict, zone_id: str, impact, severity_weight: float) -> None:
        if zone_id not in factors:
            return
        f = factors[zone_id]
        f["saturation"] = _clamp(f["saturation"] + impact.saturation_delta * severity_weight, 0.0, 2.0)
        f["attendance"] = _clamp(f["attendance"] + impact.attendance_delta * severity_weight, 0.0, 2.0)
        f["resource"] = _clamp(f["resource"] + impact.resource_delta * severity_weight, 0.0, 2.0)

    def _apply_specific_overrides(self, db: Session, event_day_id: str, dt: datetime, zones: list[Zone], factors: dict) -> dict:
        specific_overrides = state_override_crud.get_active_overrides(db, event_day_id, dt)
        specific_overrides = [o for o in specific_overrides if o.zone_type_id is not None]

        for override in specific_overrides:
            zt = zone_type_crud.get(db, override.zone_type_id)
            if not zt:
                continue
            state = override.event_state
            for zone in zones:
                if zone.type == zt.slug:
                    zone_factors = self._get_factors_for_zone(db, event_day_id, zt.id, state.id, state.slug, zone)
                    factors[zone.id] = zone_factors

        return factors

    def _get_factors_for_zone(self, db: Session, event_day_id: str, zone_type_id: str, state_id: str, state_slug: str, zone: Zone) -> dict:
        edzf = edzf_crud.get_by_combo(db, event_day_id, zone_type_id, state_id)
        if edzf is not None:
            return {
                "saturation": _clamp(edzf.saturation_factor, 0.0, 2.0),
                "attendance": _clamp(edzf.attendance_factor, 0.0, 2.0),
                "resource": _clamp(edzf.resource_factor, 0.0, 2.0),
                "priority": _clamp(edzf.priority_weight, 0, 200),
            }
        zt = zone_type_crud.get(db, zone_type_id)
        if zt is not None:
            defaults = zt.default_factors.get(state_slug, {})
            return {
                "saturation": _clamp(defaults.get("saturation", 1.0), 0.0, 2.0),
                "attendance": _clamp(defaults.get("attendance", 1.0), 0.0, 2.0),
                "resource": _clamp(defaults.get("resource", 1.0), 0.0, 2.0),
                "priority": int(_clamp(defaults.get("priority", 0), 0, 200)),
            }
        return {"saturation": 1.0, "attendance": 1.0, "resource": 1.0, "priority": 0}

    def _generate_predictions(self, zones: list[Zone], factors: dict) -> list[dict]:
        predictions = []
        for zone in zones:
            f = factors.get(zone.id, {"saturation": 1.0, "attendance": 1.0, "resource": 1.0, "priority": 0})

            attendance_predicha = 1.0 * f["attendance"]

            denominator = max(zone.capacity * f["saturation"], 1)
            saturation_predicha = _clamp(1.0 - (zone.available_capacity / denominator), 0.0, 1.0)

            recurso_requerido = 1.0 * f["resource"]

            priority_score = f["priority"] * f["attendance"]

            predictions.append({
                "id": zone.id,
                "name": zone.name,
                "type": zone.type,
                "factores": {
                    "saturation": f["saturation"],
                    "attendance": f["attendance"],
                    "resource": f["resource"],
                    "priority": f["priority"],
                },
                "prediccion": {
                    "saturation_predicha": saturation_predicha,
                    "attendance_predicha": attendance_predicha,
                    "recurso_requerido": recurso_requerido,
                    "priority_score": priority_score,
                },
            })
        return predictions

    def _baseline_response(self, event_id: str, db: Session) -> dict:
        zones = self._get_event_zones(db, event_id)
        predictions = []
        for zone in zones:
            predictions.append({
                "id": zone.id,
                "name": zone.name,
                "type": zone.type,
                "factores": {
                    "saturation": 1.0,
                    "attendance": 1.0,
                    "resource": 1.0,
                    "priority": 0,
                },
                "prediccion": {
                    "saturation_predicha": 1.0 - (zone.available_capacity / max(zone.capacity, 1)),
                    "attendance_predicha": 1.0,
                    "recurso_requerido": 1.0,
                    "priority_score": 0.0,
                },
            })
        return {
            "estado_actual": None,
            "override_activo": None,
            "zonas": predictions,
        }
