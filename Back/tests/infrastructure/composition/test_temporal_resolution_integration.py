"""Corrección temporal — resolución consistente entre módulos.

Verifica que PredictionModule, ParkingModule y RecommendationModule resuelven
la MISMA jornada activa para instantes nocturnos que cruzan medianoche
(EventDay 14/07 con ventana [1200, 1680) = 20:00 -> 04:00).

Sin base de datos: sesión AsyncMock con el mismo patrón del resto de la suite.
Los timestamps usan explícitamente America/Argentina/Buenos_Aires.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from src.domain.entities.zone import Zone
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import ActionType, RequestedAction
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.infrastructure.composition.parking_module import ParkingModule
from src.infrastructure.composition.prediction_module import PredictionModule
from src.infrastructure.composition.recommendation_module import RecommendationModule

AR = ZoneInfo("America/Argentina/Buenos_Aires")

EVENT_ID = "event-nightly"
DAY_ID = "11111111-1111-1111-1111-111111111111"
OP_ID = "99999999-0000-0000-0000-000000000001"
ATTENDANCE_ID = "55555555-5555-5555-5555-555555555555"
PHASE_ID = "44444444-4444-4444-4444-444444444444"

ZT_IDS = {
    "estacionamiento": "22222222-2222-2222-2222-222222222222",
    "comida": "33333333-3333-3333-3333-333333333333",
}

PARKING_IDS = {
    "A": UUID("a0000000-0000-0000-0000-000000000001"),
    "B": UUID("a0000000-0000-0000-0000-000000000002"),
}
COMIDA_ID = UUID("c0000000-0000-0000-0000-000000000001")

REF_LAT = -31.4135
REF_LNG = -64.1811


def _scalars_result(models):
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.__iter__.return_value = iter(models)
    scalars_mock.all.return_value = list(models)
    result.scalars = MagicMock(return_value=scalars_mock)
    return result


def _scalar_one_result(model):
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=model)
    return result


def _first_result(model):
    """Fila unica accesible por `.first()` y por `.scalars().first()`.

    La misma tabla se lee con las dos formas segun quien la consulta: el snapshot
    del Knowledge Model usa `.scalars().first()`, mientras que otros lectores
    usan `.first()` a secas. Con un helper que no cubriera ambos, `json.dumps`
    del hash se comia un MagicMock y reventaba con
    `TypeError: Object of type MagicMock is not JSON serializable`.
    """
    result = MagicMock()
    result.first = MagicMock(return_value=model)
    scalars_mock = MagicMock()
    scalars_mock.first = MagicMock(return_value=model)
    scalars_mock.all = MagicMock(return_value=[model] if model is not None else [])
    scalars_mock.__iter__ = MagicMock(return_value=iter([model] if model is not None else []))
    result.scalars = MagicMock(return_value=scalars_mock)
    result.one_or_none = MagicMock(return_value=model)
    result.scalar_one_or_none = MagicMock(return_value=model)
    return result


def _one_result(row):
    result = MagicMock()
    result.one_or_none = MagicMock(return_value=row)
    return result


class CapturingEngine:
    def __init__(self) -> None:
        self.captured_event_day = None

    def predict(
        self,
        *,
        timestamp: datetime,
        zones,
        zone_behaviors,
        operational_phases,
        attendance_level,
        event_day,
        events,
        config=None,
        knowledge_model_version_id=None,
    ) -> TerritorialPrediction:
        self.captured_event_day = event_day
        return TerritorialPrediction(
            timestamp=timestamp,
            zone_states=[
                ZoneState(
                    zone_id=zone.id,
                    operational_state="NORMAL",
                    active_restriction=None,
                    type=zone.type,
                    subtipo=zone.subtipo,
                )
                for zone in zones
            ],
            active_phase_id=UUID(OP_ID),
            active_event_day_phase_id=UUID(PHASE_ID),
        )


def _zone_row(zone_id, name, ztype, capacity):
    return SimpleNamespace(
        id=str(zone_id),
        name=name,
        type=ztype,
        subtipo=None,
        capacity=capacity,
        available_capacity=capacity,
        latitude=REF_LAT,
        longitude=REF_LNG,
    )


zone_type_rows = [
    SimpleNamespace(slug="estacionamiento", id=ZT_IDS["estacionamiento"]),
    SimpleNamespace(slug="comida", id=ZT_IDS["comida"]),
]
ref_row = SimpleNamespace(
    reference_point_latitude=REF_LAT,
    reference_point_longitude=REF_LNG,
)
all_zone_rows = [
    _zone_row(PARKING_IDS["A"], "Parking A", "estacionamiento", 500),
    _zone_row(PARKING_IDS["B"], "Parking B", "estacionamiento", 400),
    _zone_row(COMIDA_ID, "Patio Comida", "comida", 200),
]
parking_rows = all_zone_rows[:2]
behavior_rows = [
    SimpleNamespace(
        id=f"88888888-0000-0000-0000-00000000000{i}",
        zone_type_id=ZT_IDS[slug],
        operational_phase_id=PHASE_ID,
        density_factor=density,
        flow_restriction="OPEN",
        # Campos que ademas lee el snapshot del Knowledge Model: se serializan tal
        # cual en `snapshot["zone_behaviors"]`, asi que la fila debe traerlos.
        saturation_factor=0.5,
        availability_factor=0.5,
        resource_factor=0.5,
        priority_weight=1.0,
    )
    for i, (slug, density) in enumerate(
        [("estacionamiento", 0.8), ("comida", 0.6)],
        start=1,
    )
]
ed_row = SimpleNamespace(
    id=DAY_ID,
    date=date(2026, 7, 14),
    attendance_level_id=ATTENDANCE_ID,
    operational_profile_id=UUID(OP_ID),
    operational_start_min=1200,
    operational_end_min=1680,
    estimated_vehicles=8000,
    average_parking_duration=4.0,
    phases=[
        SimpleNamespace(
            id=PHASE_ID,
            operational_phase_id=OP_ID,
            start_min=1200,
            end_min=1680,
            intensity=0.5,
        )
    ],
)
attendance_row = SimpleNamespace(
    id=ATTENDANCE_ID,
    event_id=EVENT_ID,
    name="Normal",
    min_people=10000,
    max_people=25000,
)
# Jornada con ventana operativa que NO contiene el instante que usan los tests de
# "inactivo" (04:01 AR = minuto 1681). Sirve para que `resolve_active_event_day`
# la descarte por ventana, que es como decide, en vez de por fecha.
inactive_ed_row = SimpleNamespace(
    id=DAY_ID,
    date=date(2026, 7, 15),
    attendance_level_id=ATTENDANCE_ID,
    operational_profile_id=UUID(OP_ID),
    operational_start_min=600,
    operational_end_min=1200,
    estimated_vehicles=8000,
    average_parking_duration=4.0,
    phases=[
        SimpleNamespace(
            id=PHASE_ID,
            operational_phase_id=OP_ID,
            start_min=600,
            end_min=1200,
            intensity=0.5,
        )
    ],
)
phase_rows = [SimpleNamespace(id=OP_ID, name="Nocturna", sort_order=1)]
# `PredictionModule` y `RecommendationModule` capturan un snapshot del Knowledge
# Model antes de predecir (`KnowledgeModelSnapshotService.capture_current_snapshot`).
# Esa lectura exige filas reales: si `recommendation_config` o `stage4_config` vienen
# vacias, el servicio levanta `ValueError("... is not configured")`. El
# `side_effect` posicional no tenia entradas para estas consultas, asi que el
# recorrido terminaba en `StopIteration`.
recommendation_config_row = SimpleNamespace(
    low_density_saturation_threshold=0.2,
    low_density_reasoning_threshold=0.3,
    regulated_penalty=0.1,
    vip_bonus=0.05,
    staff_bonus=0.02,
    mobility_penalty=0.01,
)
stage4_config_row = SimpleNamespace(
    saturation_high_threshold=1.2,
    saturation_moderate_threshold=0.8,
)


def _mock_session(*, module: str, active: bool) -> AsyncMock:
    """Construye la sesión según el flujo del módulo.

    Las respuestas se despachan por nombre de tabla, no por posición. Antes era
    una lista `side_effect=[...]` que se consumía en orden, y cualquier consulta
    nueva en producción la agotaba (`StopIteration`) sin decir nada del dominio.

    `active=True` -> la jornada del día está activa.
    `active=False` -> ninguna jornada activa (los módulos devuelven None/vacío).
    """
    if module not in ("parking", "prediction", "recommendation"):
        raise ValueError(f"unknown module {module}")

    session = AsyncMock()

    responses: dict[str, MagicMock] = {
        "zone_types": _scalars_result(zone_type_rows),
        "events": _one_result(ref_row),
        "zone_behaviors": _scalars_result(behavior_rows),
        # Sin eventos operativos activos.
        "operational_events": _scalars_result([]),
        # Knowledge Model snapshot: exige filas, ver comentario de las constantes.
        # Ver `_first_result`: la fila tiene que ser alcanzable por `.first()` y por
        # `.scalars().first()`, o el `json.dumps` del hash se come un MagicMock.
        "recommendation_config": _first_result(recommendation_config_row),
        "stage4_config": _first_result(stage4_config_row),
        "knowledge_model_versions": _scalars_result([]),
    }
    if active:
        responses["event_days"] = _scalar_one_result(ed_row)
        responses["attendance_levels"] = _scalar_one_result(attendance_row)
        responses["operational_phases"] = _scalars_result(phase_rows)
    else:
        # La jornada EXISTE pero su ventana operativa no contiene el instante.
        # `resolve_active_event_day` decide por ventana, no por fecha: sin fila
        # devolvía None y el recorrido moría antes de llegar al final. Con una
        # ventana ajena al instante se exercise el mismo camino que en producción:
        # jornada presente, inactiva.
        responses["event_days"] = _scalar_one_result(inactive_ed_row)

    async def _router(stmt) -> MagicMock:
        sql = str(stmt).lower()
        match = re.search(r"\bfrom\s+([a-z_][a-z0-9_]*)", sql)
        table = match.group(1) if match else ""
        if table == "zones":
            # Dos consultas distintas a la misma tabla: la del ContextEngine pide
            # todas las zonas del evento; la de `ParkingModule` (puente ETAPA 4)
            # filtra por `type = estacionamiento`. Se distinguen por el WHERE.
            if "'estacionamiento'" in sql:
                return _scalars_result(parking_rows)
            return _scalars_result(all_zone_rows)
        if table == "service_configs":
            # Permanencia Parking V1: override por jornada + default global.
            # Sin filas cae al `EventDay.average_parking_duration`.
            return _scalar_one_result(None)
        result = responses.get(table)
        if result is not None:
            return result
        # Consulta no modelada: vacía en vez de agotar el mock. Deja el fallo en la
        # aserción del test, no en un StopIteration que no dice nada del dominio.
        return _scalars_result([])

    session.execute = AsyncMock(side_effect=_router)
    return session


def _ar(day: int, hour: int, minute: int) -> datetime:
    return datetime(2026, 7, day, hour, minute, tzinfo=AR)


def _user_context() -> UserContext:
    return UserContext(
        user_id=UUID("99999999-9999-9999-9999-999999999999"),
        access_level=AccessLevel.STANDARD,
    )


def _mobility_context() -> MobilityContext:
    return MobilityContext(
        current_zone_id=None,
        speed=1.5,
        accessibility_required=False,
    )


class TestConsistentNightlyResolution:
    @pytest.mark.parametrize(
        "instant",
        [_ar(15, 0, 30), _ar(15, 3, 59)],
    )
    async def test_prediction_resolves_nightly_day(self, instant: datetime) -> None:
        engine = CapturingEngine()
        with patch(
            "src.infrastructure.composition.prediction_module.ContextEngine",
            return_value=engine,
        ):
            prediction = await PredictionModule(
                _mock_session(module="prediction", active=True)
            ).execute(timestamp=instant, event_id=EVENT_ID)

        assert prediction is not None
        assert engine.captured_event_day is not None
        assert engine.captured_event_day.id == UUID(DAY_ID)
        assert engine.captured_event_day.event_date == date(2026, 7, 14)

    @pytest.mark.parametrize(
        "instant",
        [_ar(15, 0, 30), _ar(15, 3, 59)],
    )
    async def test_parking_resolves_nightly_day(self, instant: datetime) -> None:
        result = await ParkingModule(
            _mock_session(module="parking", active=True)
        ).execute(timestamp=instant, event_id=EVENT_ID)

        assert result is not None
        assert result.estimated_vehicles == 8000
        assert result.phases[0].event_day_id == UUID(DAY_ID)
        assert [p.start_min for p in result.phases] == [1200]
        assert [p.end_min for p in result.phases] == [1680]

    @pytest.mark.parametrize(
        "instant",
        [_ar(15, 0, 30), _ar(15, 3, 59)],
    )
    async def test_recommendation_resolves_nightly_day(
        self, instant: datetime
    ) -> None:
        engine = CapturingEngine()
        with patch(
            "src.infrastructure.composition.recommendation_module.ContextEngine",
            return_value=engine,
        ):
            module = RecommendationModule(
                _mock_session(module="recommendation", active=True)
            )
            recs, prediction = await module.execute(
                timestamp=instant,
                event_id=EVENT_ID,
                user_context=_user_context(),
                mobility_context=_mobility_context(),
                requested_action=RequestedAction(
                    action_type=ActionType.SEEK_PARKING
                ),
                limit=5,
            )

        assert prediction is not None
        assert engine.captured_event_day is not None
        assert engine.captured_event_day.id == UUID(DAY_ID)
        assert all(isinstance(r, ZoneRecommendation) for r in recs)


class TestConsistentInactiveInstant:
    """04:01 AR (minuto 1681) ya no cae en [1200, 1680): todos los módulos
    deben devolver None / vacío."""

    INSTANT = _ar(15, 4, 1)

    async def test_prediction_returns_none(self) -> None:
        with patch(
            "src.infrastructure.composition.prediction_module.ContextEngine",
            return_value=CapturingEngine(),
        ):
            prediction = await PredictionModule(
                _mock_session(module="prediction", active=False)
            ).execute(timestamp=self.INSTANT, event_id=EVENT_ID)

        assert prediction is None

    async def test_parking_returns_none(self) -> None:
        result = await ParkingModule(
            _mock_session(module="parking", active=False)
        ).execute(timestamp=self.INSTANT, event_id=EVENT_ID)

        assert result is None

    async def test_recommendation_returns_empty(self) -> None:
        with patch(
            "src.infrastructure.composition.recommendation_module.ContextEngine",
            return_value=CapturingEngine(),
        ):
            recs, prediction = await RecommendationModule(
                _mock_session(module="recommendation", active=False)
            ).execute(
                timestamp=self.INSTANT,
                event_id=EVENT_ID,
                user_context=_user_context(),
                mobility_context=_mobility_context(),
                requested_action=RequestedAction(
                    action_type=ActionType.SEEK_PARKING
                ),
                limit=5,
            )

        assert prediction is None
        assert recs == []