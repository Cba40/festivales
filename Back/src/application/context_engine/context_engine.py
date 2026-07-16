from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from uuid import UUID

from src.application.context_engine.stage1_context_resolution import (
    resolve_contextual_phase,
)
from src.application.context_engine.stage2_event_evaluation import (
    apply_dynamic_events,
)
from src.application.context_engine.stage3_zone_behavior_application import (
    apply_zone_behaviors,
)
from src.application.context_engine.stage4_zone_state_derivation import (
    derive_zone_states,
)
from src.application.context_engine.stage5_prediction_assembly import (
    assemble_prediction,
)
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.event_day import EventDay
from src.domain.entities.operational_event import OperationalEvent
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import ZoneBehavior
from src.domain.value_objects.territorial_prediction import TerritorialPrediction


class ContextEngine:
    def predict(
        self,
        *,
        timestamp: datetime,
        zones: Sequence[Zone],
        zone_behaviors: Mapping[tuple[UUID, UUID], ZoneBehavior],
        operational_phases: Mapping[UUID, OperationalPhase],
        attendance_level: AttendanceLevel,
        event_day: EventDay,
        events: Sequence[OperationalEvent],
    ) -> TerritorialPrediction:
        active_event_day_phase, active_operational_phase = resolve_contextual_phase(
            event_day,
            operational_phases,
            timestamp,
        )

        evaluation_result = apply_dynamic_events(
            active_operational_phase,
            active_event_day_phase,
            events,
            timestamp,
        )

        zone_behavior_result = apply_zone_behaviors(
            zones,
            zone_behaviors,
            attendance_level,
            evaluation_result,
        )

        zone_states = derive_zone_states(
            zone_behavior_result,
            zones,
            events,
            evaluation_result,
        )

        prediction = assemble_prediction(
            zone_states,
            active_operational_phase,
            active_event_day_phase,
            timestamp,
        )

        return prediction
