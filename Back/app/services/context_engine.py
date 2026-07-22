"""Context Engine P3.0 — Motor de Inferencia Territorial Determinista."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.operational_event import list_active_by_event_day
from app.crud.operational_phase import list_by_profile as list_phases_by_profile
from app.crud.zone_behavior import list_by_phase as list_zone_behaviors_by_phase
from app.models.attendance_level import AttendanceLevel
from app.models.event_day import EventDay
from app.models.incident import Incident
from app.models.operational_event_modifier import OperationalEventModifier
from app.models.zone import Zone
from app.models.zone_type import ZoneType
from app.schemas.territorial_prediction import TerritorialPrediction, ZonePrediction

logger = logging.getLogger(__name__)

_SEVERITY_WEIGHTS = {
    "baja": 0.25,
    "media": 0.5,
    "alta": 0.75,
    "critica": 1.0,
}


class ContextEngineService:
    """Motor de inferencia contextual territorial.

    No modela eventos. Modela el comportamiento operativo del territorio
    durante un evento masivo. Completamente determinista. Sin IA.
    """

    async def predict(
        self,
        db: AsyncSession,
        event_id: str,
        datetime_actual: datetime,
    ) -> TerritorialPrediction:
        # ═══════════════════════════════════════════
        # PASO 1 — Jornada activa (soporta cruce de medianoche)
        # ═══════════════════════════════════════════
        fecha_actual = datetime_actual.date()
        result = await db.execute(
            select(EventDay).where(
                EventDay.event_id == event_id,
                EventDay.is_active == True,
                EventDay.date.in_([fecha_actual, fecha_actual - timedelta(days=1)]),
            ).order_by(EventDay.date.desc())
        )
        candidatas: list[EventDay] = list(result.scalars().all())

        jornada_activa = None
        current_min = 0

        for candidata in candidatas:
            inicio_jornada = datetime(
                candidata.date.year, candidata.date.month, candidata.date.day,
                tzinfo=timezone.utc,
            ) + timedelta(minutes=candidata.operational_start_min)

            diff_segundos = (datetime_actual - inicio_jornada).total_seconds()
            current_min_candidata = int(diff_segundos // 60)

            if 0 <= current_min_candidata < candidata.operational_end_min:
                jornada_activa = candidata
                current_min = current_min_candidata
                break

        if jornada_activa is None:
            return await self._prediccion_base(db, event_id, datetime_actual)

        # ═══════════════════════════════════════════
        # PASO 2 — Resolver OperationalPhase
        # ═══════════════════════════════════════════
        fases = await list_phases_by_profile(db, jornada_activa.operational_profile_id)
        phase = None
        fase_usada_fallback = False

        for p in fases:
            if p.start_min <= current_min < p.end_min:
                phase = p
                break

        if phase is None and fases:
            phase = fases[0]
            fase_usada_fallback = True

        if phase is None:
            return await self._prediccion_base(db, event_id, datetime_actual)

        # ═══════════════════════════════════════════
        # PASO 3 — Derivar AttendanceLevel
        # ═══════════════════════════════════════════
        estimated = jornada_activa.estimated_attendance
        al_result = await db.execute(
            select(AttendanceLevel).where(
                AttendanceLevel.event_id == event_id,
                AttendanceLevel.min_people <= estimated,
                or_(
                    AttendanceLevel.max_people.is_(None),
                    AttendanceLevel.max_people >= estimated,
                ),
            )
        )
        attendance_level_obj = al_result.scalar_one_or_none()
        global_multiplier = attendance_level_obj.global_multiplier if attendance_level_obj else 1.0
        attendance_level_name = attendance_level_obj.name if attendance_level_obj else "default"

        # ═══════════════════════════════════════════
        # PASO 4 — Resolver ZoneBehavior por zona
        # ═══════════════════════════════════════════
        behavior_list = await list_zone_behaviors_by_phase(db, phase.id)
        zb_by_zone_type: dict[str, dict] = {}
        for zb in behavior_list:
            zb_by_zone_type[zb.zone_type_id] = {
                "saturation": float(zb.density_factor),
                "attendance": float(zb.availability_factor),
                "resource": float(zb.resource_factor),
                "priority_weight": float(zb.priority_weight),
                "flow_restriction": zb.flow_restriction,
            }

        # ═══════════════════════════════════════════
        # PASO 5 — Aplicar OperationalEvents activos
        # ═══════════════════════════════════════════
        active_events = await list_active_by_event_day(db, jornada_activa.id, current_min)

        event_types = {e.event_type for e in active_events}
        modifiers_by_type: dict[str, list] = {}
        for et in event_types:
            mod_result = await db.execute(
                select(OperationalEventModifier).where(
                    OperationalEventModifier.event_type == et
                )
            )
            modifiers_by_type[et] = list(mod_result.scalars().all())

        for evento in active_events:
            mods = modifiers_by_type.get(evento.event_type, [])
            for zt_id, factors in zb_by_zone_type.items():
                for mod in mods:
                    if mod.zone_type_id is None or mod.zone_type_id == zt_id:
                        factors["saturation"] *= float(mod.saturation_multiplier)
                        factors["attendance"] *= float(mod.availability_multiplier)
                        factors["priority_weight"] += float(mod.priority_modifier)

        # ═══════════════════════════════════════════
        # PASO 6 — Corregir con incidentes activos
        # ═══════════════════════════════════════════
        inc_result = await db.execute(
            select(Incident).where(
                Incident.event_id == event_id,
                Incident.status.in_(["abierto", "en_curso"]),
            )
        )
        active_incidents: list[Incident] = list(inc_result.scalars().all())

        for incident in active_incidents:
            severity_weight = _SEVERITY_WEIGHTS.get(incident.severity, 0.5)
            for impact in incident.incident_impacts:
                if impact.zone_type_id in zb_by_zone_type:
                    f = zb_by_zone_type[impact.zone_type_id]
                    f["saturation"] += impact.saturation_delta * severity_weight
                    f["attendance"] += impact.attendance_delta * severity_weight
                    f["resource"] += impact.resource_delta * severity_weight

        # ═══════════════════════════════════════════
        # PASO 7 — Generar TerritorialPrediction por zona
        # ═══════════════════════════════════════════
        zone_result = await db.execute(
            select(Zone).where(Zone.event_id == event_id)
        )
        zones: list[Zone] = list(zone_result.scalars().all())

        zone_type_slug_map: dict[str, str] = {}
        zt_result = await db.execute(select(ZoneType))
        for zt in zt_result.scalars().all():
            zone_type_slug_map[zt.slug] = zt.id

        predictions: list[ZonePrediction] = []

        for zone in zones:
            zt_id = zone_type_slug_map.get(zone.type)
            factor = zb_by_zone_type.get(zt_id, {
                "saturation": 1.0,
                "attendance": 1.0,
                "resource": 1.0,
                "priority_weight": 1.0,
            }) if zt_id else {
                "saturation": 1.0,
                "attendance": 1.0,
                "resource": 1.0,
                "priority_weight": 1.0,
            }

            base_attendance = 1.0
            base_resource = 1.0

            attendance_predicha = base_attendance * factor["attendance"] * global_multiplier

            capacity = max(zone.capacity, 1)
            denominator = capacity * factor["saturation"] * global_multiplier
            if denominator <= 0:
                saturation_predicha = 1.0
            else:
                saturation_predicha = max(0.0, 1.0 - (zone.available_capacity / denominator))

            recurso_requerido = base_resource * factor["resource"] * global_multiplier

            priority_score_raw = factor["priority_weight"] * factor["attendance"]
            priority_score = max(0.0, min(1.0, priority_score_raw))

            confidence = self._calcular_confianza(
                zt_id, zb_by_zone_type, fase_usada_fallback, active_events, active_incidents,
            )

            predictions.append(ZonePrediction(
                zone_id=zone.id,
                zone_type=zone.type,
                saturation_predicted=round(saturation_predicha, 4),
                attendance_predicted=round(attendance_predicha, 4),
                resource_required=round(recurso_requerido, 4),
                priority_score=round(priority_score, 4),
                confidence=round(confidence, 4),
                recommendation=None,
            ))

        active_event_types = [e.event_type for e in active_events]

        return TerritorialPrediction(
            zones=predictions,
            current_phase=phase.name,
            attendance_level=attendance_level_name,
            active_events=active_event_types,
            timestamp=datetime_actual,
        )

    def _calcular_confianza(
        self,
        zone_type_id: str | None,
        zb_by_zone_type: dict[str, dict],
        fase_usada_fallback: bool,
        active_events: list,
        active_incidents: list,
    ) -> float:
        if zone_type_id and zone_type_id not in zb_by_zone_type:
            return 0.5
        if fase_usada_fallback:
            return 0.7
        return 1.0

    async def _prediccion_base(
        self,
        db: AsyncSession,
        event_id: str,
        datetime_actual: datetime,
    ) -> TerritorialPrediction:
        zone_result = await db.execute(
            select(Zone).where(Zone.event_id == event_id)
        )
        zones: list[Zone] = list(zone_result.scalars().all())

        predictions: list[ZonePrediction] = []
        for zone in zones:
            capacity = max(zone.capacity, 1)
            saturation_predicha = max(0.0, 1.0 - (zone.available_capacity / capacity))

            predictions.append(ZonePrediction(
                zone_id=zone.id,
                zone_type=zone.type,
                saturation_predicted=round(saturation_predicha, 4),
                attendance_predicted=1.0,
                resource_required=1.0,
                priority_score=0.0,
                confidence=0.5,
                recommendation=None,
            ))

        return TerritorialPrediction(
            zones=predictions,
            current_phase="",
            attendance_level="default",
            active_events=[],
            timestamp=datetime_actual,
        )
