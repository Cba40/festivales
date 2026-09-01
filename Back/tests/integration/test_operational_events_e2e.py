"""Tests E2E — Fase 6 RFC-OPERATIONAL-EVENTS-V1.

Valida el flujo END-TO-END del módulo Eventos Imprevistos V1:

    operational_events (fila persistida por POST /operational-events, F2)
        -> OperationalEventAdapter.find_active_by_timestamp   (F3)
        -> GeneratePrediction (use case real)                 (F4)
        -> ContextEngine.predict (stage1..stage5)             (F4)
        -> TerritorialPrediction (predicción territorial)

Cubre los 5 casos de uso verificables del RFC-OPERATIONAL-EVENTS-V1 §14.

Sin PostGIS: la sesión SQLAlchemy se simula con despacho por tabla
(AsyncMock, patrón de las fases 2-3). La creación/validación de la API y el
CRUD ya se validan en F2 (`test_operational_event_v1.py`); aquí se parte de
la fila ya persistida y se recorre el pipeline completo hasta la predicción.

Consistencia numérica: `density_factor = 1.0` (valor dentro del rango [0,1]
del dominio que hace coincidir el cálculo del adapter, cuyo default es 1.0,
con el del motor). Las capacidades se eligen para que la fórmula RFC §8 dé
valores representativos dentro del clamp [-100, 100] del dominio (F1/F3) en
los casos "reducción" e "incidente"; el "cierre total" y el "aumento" ejercen
intencionalmente el clamp (RFC §8.2/F3). Resultado: `projected_density =
capacity + accumulated_impact` (RFC §10.2).
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID
from zoneinfo import ZoneInfo

from src.application.context_engine import ContextEngine
from src.application.use_cases.generate_prediction import GeneratePrediction
from src.domain.entities.attendance_level import AttendanceLevel
from src.domain.entities.event_day import EventDay
from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.operational_event import OperationalEvent
from src.domain.entities.operational_phase import OperationalPhase
from src.domain.entities.zone import Zone
from src.domain.entities.zone_behavior import FlowRestriction, ZoneBehavior
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.infrastructure.composition.adapters.operational_event_adapter import (
    OperationalEventAdapter,
    compute_impact,
)

AR = ZoneInfo("America/Argentina/Buenos_Aires")

EVENT_DAY_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
OP_PHASE = "99999999-0000-0000-0000-000000000001"
ED_PHASE = "44444444-0000-0000-0000-000000000001"
ATTENDANCE_ID = "55555555-0000-0000-0000-000000000001"

ZT_COMIDA = UUID("cccccccc-0000-0000-0000-000000000001")
ZT_ESCENARIO = UUID("cccccccc-0000-0000-0000-000000000002")
ZT_PLAZA = UUID("cccccccc-0000-0000-0000-000000000003")
ZT_BANO = UUID("cccccccc-0000-0000-0000-000000000004")

ZONE_ACCESO = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa1"
ZONE_ESCENARIO = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa2"
ZONE_PLAZA = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa3"
ZONE_BANOS = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4"

# Ventana compartida 20:00–22:00 y evaluación a las 21:00 (RFC §14).
TS_START = datetime(2026, 8, 30, 20, 0, tzinfo=AR)
TS_END = datetime(2026, 8, 30, 22, 0, tzinfo=AR)
TS = datetime(2026, 8, 30, 21, 0, tzinfo=AR)

# Fase operativa única [16:00, 23:00): contiene el minuto 1260 de las 21:00.
DAY_PHASE_ROWS = [
    SimpleNamespace(
        event_day_id=EVENT_DAY_ID,
        operational_phase_id=OP_PHASE,
        start_min=960,
        end_min=1380,
    ),
]

ED_PHASE_ENTITY = EventDayPhase(
    event_day_id=UUID(EVENT_DAY_ID),
    operational_phase_id=UUID(OP_PHASE),
    start_min=960,
    end_min=1380,
    id=UUID(ED_PHASE),
)

EVENT_DAY = EventDay(
    id=UUID(EVENT_DAY_ID),
    event_date=datetime(2026, 8, 30).date(),
    operational_profile_id=UUID("dddddddd-0000-0000-0000-000000000001"),
    attendance_level_id=UUID(ATTENDANCE_ID),
    operational_start_min=960,
    operational_end_min=1380,
    phases=(ED_PHASE_ENTITY,),
)

OPERATIONAL_PHASE = OperationalPhase(
    id=UUID(OP_PHASE),
    name="Escenario",
    sequence_order=1,
)

OPERATIONAL_PHASES = {UUID(OP_PHASE): OPERATIONAL_PHASE}

ATTENDANCE_LEVEL = AttendanceLevel(
    id=ATTENDANCE_ID,
    name="Normal",
    min_people=10000,
    max_people=25000,
)

ZONES = {
    "acceso": {
        "id": ZONE_ACCESO,
        "name": "Acceso Norte",
        "zt": ZT_COMIDA,
        "capacity": 100,
        "type": "comida",
        "subtipo": None,
        "slug": "comida",
    },
    "escenario": {
        "id": ZONE_ESCENARIO,
        "name": "Escenario Principal",
        "zt": ZT_ESCENARIO,
        "capacity": 2000,
        "type": "escenario",
        "subtipo": None,
        "slug": "escenario",
    },
    "plaza": {
        "id": ZONE_PLAZA,
        "name": "Plaza Central",
        "zt": ZT_PLAZA,
        "capacity": 500,
        "type": "plaza",
        "subtipo": None,
        "slug": "plaza",
    },
    "banos": {
        "id": ZONE_BANOS,
        "name": "Bano Zona A",
        "zt": ZT_BANO,
        "capacity": 300,
        "type": "servicios",
        "subtipo": "banos",
        "slug": "bano",
    },
}


# ---------------------------------------------------------------------------
# Infraestructura simulada (patrón F2/F3: sesión AsyncMock, sin SQL/postgis)
# ---------------------------------------------------------------------------

def _scalars_result(models):
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = list(models)
    result.scalars = MagicMock(return_value=scalars)
    return result


def _all_result(rows):
    result = MagicMock()
    result.all = MagicMock(return_value=list(rows))
    return result


def _make_session(
    event_rows,
    *,
    zone_rows,
    zone_type_rows,
):
    """Sesión con despacho por tabla; replica el predicado temporal+is_active
    del SQL emitido por `OperationalEventAdapter.find_active_by_timestamp`.
    """
    day_rows = [SimpleNamespace(id=EVENT_DAY_ID, date=datetime(2026, 8, 30).date())]

    def fake_execute(stmt, *args, **kwargs):
        sql = str(stmt)
        if "zone_behaviors" in sql:
            return _scalars_result([])
        if "zone_types" in sql:
            return _scalars_result(zone_type_rows)
        if "operational_events" in sql:
            active = [
                row
                for row in event_rows
                if row.is_active
                and row.start_timestamp <= TS
                and row.end_timestamp > TS
            ]
            return _scalars_result(active)
        if "zones" in sql:
            return _all_result(zone_rows)
        if "event_day_phases" in sql:
            return _scalars_result(DAY_PHASE_ROWS)
        if "event_days" in sql:
            return _all_result(day_rows)
        raise AssertionError(f"unexpected statement: {sql}")

    async def async_fake_execute(stmt, *args, **kwargs):
        return fake_execute(stmt, *args, **kwargs)

    session = MagicMock()
    session.execute = async_fake_execute
    return session


class _PreloadedEventDayRepository:
    """EventDayRepository que devuelve la jornada simulada (un solo EventDay)."""

    def __init__(self, event_day: EventDay) -> None:
        self._event_day = event_day

    async def find_by_date(self, target_date):
        if self._event_day is not None and self._event_day.event_date == target_date:
            return self._event_day
        return None


class _CapturePredictionRepository:
    """PredictionRepository en memoria que captura la predicción generada."""

    def __init__(self) -> None:
        self.saved: TerritorialPrediction | None = None

    async def save(self, prediction: TerritorialPrediction) -> TerritorialPrediction:
        self.saved = prediction
        return prediction

    async def find_by_timestamp(self, timestamp):
        if self.saved is not None and self.saved.timestamp == timestamp:
            return self.saved
        return None


def _event_row(
    rid: str,
    zone_id: str,
    *,
    event_type: str,
    effect_type: str,
    effect_value: int | None,
    is_incident: bool = False,
    is_active: bool = True,
):
    """Representa la fila persistida por POST /operational-events (F2)."""
    return SimpleNamespace(
        id=rid,
        event_day_id=EVENT_DAY_ID,
        zone_id=zone_id,
        event_type=event_type,
        description=None,
        effect_type=effect_type,
        effect_value=effect_value,
        is_incident=is_incident,
        start_timestamp=TS_START,
        end_timestamp=TS_END,
        is_active=is_active,
    )


def _scenario(key: str):
    """Build de la zona (dominio + fila ORM + tipo catálogo + comportamiento)."""
    spec = ZONES[key]
    zone = Zone(
        id=UUID(spec["id"]),
        name=spec["name"],
        zone_type_id=spec["zt"],
        capacity=spec["capacity"],
        type=spec["type"],
        subtipo=spec["subtipo"],
    )
    zone_row = SimpleNamespace(
        id=spec["id"],
        capacity=spec["capacity"],
        type=spec["type"],
        subtipo=spec["subtipo"],
    )
    zone_type_row = SimpleNamespace(slug=spec["slug"], id=str(spec["zt"]))
    behavior = ZoneBehavior(
        zone_type_id=spec["zt"],
        operational_phase_id=UUID(OP_PHASE),
        density_factor=1.0,
        flow_restriction=FlowRestriction.OPEN,
    )
    return {
        "zone": zone,
        "zone_row": zone_row,
        "zone_type_row": zone_type_row,
        "behaviors": {(spec["zt"], UUID(OP_PHASE)): behavior},
        "zone_id": UUID(spec["id"]),
    }


async def _run_flow(key: str, event_rows):
    """Recorre: fila persistida → adapter → GeneratePrediction → ContextEngine.

    Devuelve (eventos activos detectados por el adapter, predicción final).
    """
    scenario = _scenario(key)
    session = _make_session(
        event_rows,
        zone_rows=[scenario["zone_row"]],
        zone_type_rows=[scenario["zone_type_row"]],
    )
    adapter = OperationalEventAdapter(session)
    events = await adapter.find_active_by_timestamp(TS)

    use_case = GeneratePrediction(
        engine=ContextEngine(),
        event_day_repo=_PreloadedEventDayRepository(EVENT_DAY),
        operational_event_repo=adapter,
        prediction_repo=_CapturePredictionRepository(),
    )
    prediction = await use_case.execute(
        timestamp=TS,
        zones=[scenario["zone"]],
        zone_behaviors=scenario["behaviors"],
        attendance_level=ATTENDANCE_LEVEL,
        operational_phases=OPERATIONAL_PHASES,
    )
    return events, prediction


def _zone_state(prediction: TerritorialPrediction, zone_id: UUID):
    return next(
        (s for s in prediction.zone_states if s.zone_id == zone_id),
        None,
    )


# ---------------------------------------------------------------------------
# Casos de uso verificables del RFC §14
# ---------------------------------------------------------------------------

class TestCaso1ReduccionCapacidadPorAccidente:
    """RFC §14 Caso 1: accidente → reducción 50% → densidad 500 + razonamiento."""

    async def test_adapter_calcula_impacto_y_engine_lo_aplica(self) -> None:
        events, prediction = await _run_flow(
            "acceso",
            [
                _event_row(
                    "eeeeeeee-0000-0000-0000-000000000101",
                    ZONE_ACCESO,
                    event_type="accidente",
                    effect_type="reduccion_capacidad",
                    effect_value=50,
                    is_incident=True,
                ),
            ],
        )

        assert len(events) == 1
        assert isinstance(events[0], OperationalEvent)
        # Fórmula RFC §8.1: -round(capacity × density_factor × percentage / 100).
        assert compute_impact("reduccion_capacidad", 50, 100, 1.0) == -50
        assert events[0].impact_value == -50
        assert events[0].is_incident is True

        state = _zone_state(prediction, UUID(ZONE_ACCESO))
        assert state is not None
        assert state.projected_density == 100 + (-50)
        assert state.operational_state != "CLOSED"
        assert "Impacto de evento operativo: -50" in state.reasoning_factors
        assert "Incidente activo en zona" in state.reasoning_factors


class TestCaso2CierreTotalPorEvacuacion:
    """RFC §14 Caso 2: evacuación → cierre total → zona CLOSED."""

    async def test_impacto_cierra_la_zona(self) -> None:
        events, prediction = await _run_flow(
            "escenario",
            [
                _event_row(
                    "eeeeeeee-0000-0000-0000-000000000102",
                    ZONE_ESCENARIO,
                    event_type="evacuacion",
                    effect_type="cierre_total",
                    effect_value=None,
                    is_incident=True,
                ),
            ],
        )

        assert len(events) == 1
        # Fórmula RFC §8.2: -round(capacity × density_factor).
        assert compute_impact("cierre_total", None, 2000, 1.0) == -2000
        # El adapter normaliza a [-100, 100]; un cierre satura el rango negativo.
        assert events[0].impact_value == -100

        state = _zone_state(prediction, UUID(ZONE_ESCENARIO))
        assert state is not None
        assert state.operational_state == "CLOSED"
        assert state.active_restriction == FlowRestriction.CLOSED
        assert "Impacto de evento operativo: -100" in state.reasoning_factors
        assert "Incidente activo en zona" in state.reasoning_factors
        assert "Zona cerrada" in state.reasoning_factors


class TestCaso3AumentoDeDemandaPorConcentracion:
    """RFC §14 Caso 3: concentración → aumento 300 → densidad proyectada sube."""

    async def test_aumenta_la_densidad_proyectada(self) -> None:
        events, prediction = await _run_flow(
            "plaza",
            [
                _event_row(
                    "eeeeeeee-0000-0000-0000-000000000103",
                    ZONE_PLAZA,
                    event_type="congestion_extraordinaria",
                    effect_type="aumento_demanda",
                    effect_value=300,
                    is_incident=False,
                ),
            ],
        )

        assert len(events) == 1
        # Fórmula del adapter: impacto = +300 (efecto directo, sin clamp).
        assert compute_impact("aumento_demanda", 300, 500, 1.0) == 300
        # El adapter normaliza a [-100, 100] antes de entregar al motor (F3).
        assert events[0].impact_value == 100

        state = _zone_state(prediction, UUID(ZONE_PLAZA))
        assert state is not None
        base = 500
        assert state.projected_density == base + 100
        assert state.projected_density > base
        assert "Impacto de evento operativo: 100" in state.reasoning_factors
        assert "Incidente activo en zona" not in state.reasoning_factors


class TestCaso4IncidenteSinImpactoCuantificable:
    """RFC §14 Caso 4: incidente_operativo → impacto 0 → sólo razonamiento."""

    async def test_no_cambia_densidad_pero_agrega_razonamiento(self) -> None:
        events, prediction = await _run_flow(
            "banos",
            [
                _event_row(
                    "eeeeeeee-0000-0000-0000-000000000104",
                    ZONE_BANOS,
                    event_type="incidente_operativo",
                    effect_type="incidente_sin_impacto",
                    effect_value=None,
                    is_incident=True,
                ),
            ],
        )

        assert len(events) == 1
        assert events[0].impact_value == 0

        state = _zone_state(prediction, UUID(ZONE_BANOS))
        assert state is not None
        assert state.projected_density == 300 + 0
        assert "Incidente activo en zona" in state.reasoning_factors
        assert not any(
            factor.startswith("Impacto de evento operativo") for factor in state.reasoning_factors
        )


class TestCaso5FinalizacionAnticipada:
    """RFC §14 Caso 5: is_active=false → adapter lo omite → predicción base."""

    async def test_evento_desactivado_no_afecta_la_prediccion(self) -> None:
        event_row = _event_row(
            "eeeeeeee-0000-0000-0000-000000000105",
            ZONE_ACCESO,
            event_type="accidente",
            effect_type="reduccion_capacidad",
            effect_value=50,
            is_incident=True,
            is_active=True,
        )

        active_events, active_prediction = await _run_flow("acceso", [event_row])
        assert len(active_events) == 1
        active_state = _zone_state(active_prediction, UUID(ZONE_ACCESO))
        assert active_state.projected_density == 100 + (-50)

        event_row.is_active = False
        deactivated_events, base_prediction = await _run_flow("acceso", [event_row])
        assert deactivated_events == []
        base_state = _zone_state(base_prediction, UUID(ZONE_ACCESO))
        assert base_state.projected_density == 100
        assert not any(
            factor.startswith("Impacto de evento operativo") for factor in base_state.reasoning_factors
        )