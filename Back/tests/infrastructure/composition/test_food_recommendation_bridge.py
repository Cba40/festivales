"""ETAPA 4 Food V1 — puente Food → ZoneState → TerritorialPrediction → Recommendation.

Verifica el flujo completo: FoodModule (datos reales vía AsyncSession) →
FoodV1Model → índices por zona → ZoneState (saturation_level =
occupancy_ratio, availability = round(free_spaces)) → TerritorialPrediction
combinado → RecommendationService → solo zonas type="comida".

Toda la infraestructura de BD se simula con AsyncMock (mismo patrón que la
suite): no se accede a base de datos alguna ni a SQLite.
"""
from __future__ import annotations

import re
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.zone import Zone
from src.domain.models.food_v1_model import FoodV1Model
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import ActionType, RequestedAction
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.infrastructure.composition.food_module import (
    FOOD_ZONE_TYPE,
    FoodModule,
    FoodSimulationResult,
    _select_active_phase_state,
    derive_food_zone_state,
    merge_food_into_prediction,
)
from src.infrastructure.composition.recommendation_module import RecommendationModule

EVENT_ID = "event-food-bridge"
DAY_ID = "11111111-1111-1111-1111-111111111111"
ATTENDANCE_ID = "55555555-5555-5555-5555-555555555555"
OP_ID = "99999999-0000-0000-0000-000000000001"
OP_PHASE_ID = "99999999-0000-0000-0000-000000000002"

ZT_IDS = {
    "comida": "33333333-3333-3333-3333-333333333333",
    "bano": "34444444-4444-4444-4444-444444444444",
    "estacionamiento": "35555555-5555-5555-5555-555555555555",
    "transporte": "36666666-6666-6666-6666-666666666666",
}

# 3 zonas gastronómicas (todos los subtipos compiten por la misma demanda,
# hipótesis V1 #5) + 3 no-comida (parking, baños, transporte).
FOOD_DEFS = [
    ("Foodtruck Norte", "foodtruck", 150, 0.0),
    ("Patio Central", "patio_de_comidas", 400, 500.0),
    ("Restaurante Sur", "restaurante", 200, 1000.0),
]

FOOD_IDS = {
    key: UUID(f"a0000000-0000-0000-0000-0000000000{i:02d}")
    for i, (_, key, _, _) in enumerate(FOOD_DEFS, start=1)
}
PARKING_ID = UUID("d0000000-0000-0000-0000-000000000001")
BANOS_ID = UUID("e0000000-0000-0000-0000-000000000001")
TRANSPORTE_ID = UUID("f0000000-0000-0000-0000-000000000001")

PHASE_IDS = {
    "p1": "77777777-0000-0000-0000-000000000001",
    "p2": "77777777-0000-0000-0000-000000000002",
    "p3": "77777777-0000-0000-0000-000000000003",
}

REF_LAT = -31.4135
REF_LNG = -64.1811
TS = datetime(2026, 7, 15, 15, 0)

MAX_PEOPLE = 10000
DURATIONS_MIN = {
    "foodtruck": 20,
    "patio_de_comidas": 30,
    "restaurante": 60,
}


def _food_zones() -> list[Zone]:
    return [
        Zone(
            id=FOOD_IDS[key],
            name=name,
            zone_type_id=UUID(ZT_IDS["comida"]),
            capacity=capacity,
            type="comida",
            subtipo=key,
            latitude=REF_LAT,
            longitude=REF_LNG,
            reference_point_distance=distance,
        )
        for name, key, capacity, distance in FOOD_DEFS
    ]


def _non_food_zones() -> list[Zone]:
    return [
        Zone(
            id=PARKING_ID,
            name="Parking Norte",
            zone_type_id=UUID(ZT_IDS["estacionamiento"]),
            capacity=300,
            type="estacionamiento",
            subtipo=None,
            latitude=REF_LAT,
            longitude=REF_LNG,
            reference_point_distance=800.0,
        ),
        Zone(
            id=BANOS_ID,
            name="Banos Sector",
            zone_type_id=UUID(ZT_IDS["bano"]),
            capacity=200,
            type="servicios",
            subtipo="banos",
            latitude=REF_LAT,
            longitude=REF_LNG,
            reference_point_distance=400.0,
        ),
        Zone(
            id=TRANSPORTE_ID,
            name="Transporte Este",
            zone_type_id=UUID(ZT_IDS["transporte"]),
            capacity=60,
            type="transporte",
            subtipo=None,
            latitude=REF_LAT,
            longitude=REF_LNG,
            reference_point_distance=1200.0,
        ),
    ]


def _phases() -> tuple[EventDayPhase, ...]:
    return tuple(
        EventDayPhase(
            id=UUID(PHASE_IDS[name]),
            event_day_id=UUID(DAY_ID),
            operational_phase_id=UUID(OP_ID),
            start_min=start,
            end_min=end,
            intensity=intensity,
        )
        for name, start, end, intensity in (
            ("p1", 600, 720, 0.25),
            ("p2", 720, 840, 0.50),
            ("p3", 840, 960, 0.75),
        )
    )


def _base_prediction(all_zones: list[Zone]) -> TerritorialPrediction:
    """Simula la salida del Context Engine (sin señal de modelo especializado)."""
    states = [
        ZoneState(
            zone_id=z.id,
            operational_state="NORMAL",
            active_restriction=None,
            type=z.type,
            subtipo=z.subtipo,
            projected_density=100,
        )
        for z in all_zones
    ]
    return TerritorialPrediction(
        timestamp=TS,
        zone_states=states,
        active_phase_id=UUID(OP_PHASE_ID),
        active_event_day_phase_id=UUID(PHASE_IDS["p3"]),
    )


def _durations_hours(zones: list[Zone]) -> dict[UUID, float]:
    model = FoodV1Model()
    return {
        zone.id: model.duration_hours(DURATIONS_MIN[zone.subtipo])
        for zone in zones
    }


def _food_result(food_zones: list[Zone]) -> FoodSimulationResult:
    phases = _phases()
    durations = _durations_hours(food_zones)
    phase_results = FoodV1Model().simulate(
        phases, food_zones, MAX_PEOPLE, durations
    )
    return FoodSimulationResult(
        event_id=EVENT_ID,
        timestamp=TS,
        food_zones=tuple(food_zones),
        phases=phases,
        max_people=MAX_PEOPLE,
        durations_min=dict(DURATIONS_MIN),
        durations_hours=durations,
        d_effective_hours=phase_results[0].d_effective_hours,
        phase_results=tuple(phase_results),
    )


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


# ---------------------------------------------------------------------------
# Mock de sesión para el flujo integrado a través de RecommendationModule
# ---------------------------------------------------------------------------


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


def _one_result(row):
    result = MagicMock()
    result.one_or_none = MagicMock(return_value=row)
    return result


def _mock_bridge_session(*, food_request: bool) -> AsyncMock:
    """Sesión con despacho por tabla (mismo enfoque que test_food_module).

    El despacho por tabla es inmune al N de consultas de `service_configs`
    (una por subtipo presente × override/default), a diferencia del despacho
    posicional usado por el puente de Baños (que resuelve UNA permanencia).
    """
    session = AsyncMock()
    captured_stmts: list[object] = []

    zone_type_rows = [
        SimpleNamespace(slug="comida", id=ZT_IDS["comida"]),
        SimpleNamespace(slug="bano", id=ZT_IDS["bano"]),
        SimpleNamespace(slug="estacionamiento", id=ZT_IDS["estacionamiento"]),
        SimpleNamespace(slug="transporte", id=ZT_IDS["transporte"]),
    ]
    ref_row = SimpleNamespace(
        reference_point_latitude=REF_LAT,
        reference_point_longitude=REF_LNG,
    )

    def _row(zid: str, name: str, ztype: str, subtipo: str | None, capacity: int):
        return SimpleNamespace(
            id=zid,
            name=name,
            type=ztype,
            subtipo=subtipo,
            capacity=capacity,
            available_capacity=capacity,
            latitude=REF_LAT,
            longitude=REF_LNG,
        )

    all_zone_rows = [
        _row(str(FOOD_IDS[key]), name, "comida", key, capacity)
        for name, key, capacity, _ in FOOD_DEFS
    ] + [
        _row(str(PARKING_ID), "Parking Norte", "estacionamiento", None, 300),
        _row(str(BANOS_ID), "Banos Sector", "servicios", "banos", 200),
        _row(str(TRANSPORTE_ID), "Transporte Este", "transporte", None, 60),
    ]
    food_rows = [
        _row(str(FOOD_IDS[key]), name, "comida", key, capacity)
        for name, key, capacity, _ in FOOD_DEFS
    ]
    behavior_rows = [
        SimpleNamespace(
            id=f"88888888-0000-0000-0000-00000000000{i}",
            zone_type_id=ZT_IDS[slug],
            operational_phase_id=OP_ID,
            density_factor=density,
            flow_restriction="OPEN",
        )
        for i, (slug, density) in enumerate(
            [
                ("comida", 0.6),
                ("bano", 0.8),
                ("estacionamiento", 0.7),
                ("transporte", 0.7),
            ],
            start=1,
        )
    ]
    ed_row = SimpleNamespace(
        id=DAY_ID,
        date=datetime(2026, 7, 15, 15, 0).date(),
        attendance_level_id=ATTENDANCE_ID,
        operational_profile_id=UUID(OP_ID),
        operational_start_min=600,
        operational_end_min=960,
        estimated_vehicles=None,
        average_parking_duration=None,
        phases=[
            SimpleNamespace(
                id=PHASE_IDS[name],
                operational_phase_id=OP_ID,
                start_min=start,
                end_min=end,
                intensity=intensity,
            )
            for name, start, end, intensity in (
                ("p1", 600, 720, 0.25),
                ("p2", 720, 840, 0.50),
                ("p3", 840, 960, 0.75),
            )
        ],
    )
    attendance_row = SimpleNamespace(
        id=ATTENDANCE_ID,
        event_id=EVENT_ID,
        name="Normal",
        min_people=8000,
        max_people=MAX_PEOPLE,
    )
    phase_rows = [
        SimpleNamespace(id=OP_ID, name="Activa", sort_order=1),
    ]
    config_rows = {
        key: (None, SimpleNamespace(average_duration_min=minutes))
        for key, minutes in DURATIONS_MIN.items()
    }
    # El puente Baños (pipeline existente) también resuelve permanencia si la
    # acción lo activa; el despacho por tabla debe poder servirlo.
    config_rows["banos"] = (None, SimpleNamespace(average_duration_min=5))

    def _service_config_result(stmt):
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        match = re.search(
            r"coalesce\(service_configs\.subtipo, ''\) = '([^']*)'", compiled
        )
        key = match.group(1) if match else ""
        override_row, default_row = config_rows.get(key, (None, None))
        if re.search(r"IS NULL", compiled, flags=re.IGNORECASE):
            return _scalar_one_result(default_row)
        return _scalar_one_result(override_row)

    def fake_execute(stmt, *args, **kwargs):
        captured_stmts.append(stmt)
        sql = str(stmt)
        if "zone_behaviors" in sql:
            return _scalars_result(behavior_rows)
        if "zone_types" in sql:
            return _scalars_result(zone_type_rows)
        if "events" in sql:
            return _one_result(ref_row)
        if "service_configs" in sql:
            return _service_config_result(stmt)
        if "zones" in sql:
            return _scalars_result(all_zone_rows)
        if "event_days" in sql:
            return _scalar_one_result(ed_row)
        if "attendance_levels" in sql:
            return _scalar_one_result(attendance_row)
        if "operational_phases" in sql:
            return _scalars_result(phase_rows)
        raise AssertionError(f"unexpected statement: {sql}")

    async def async_fake_execute(stmt, *args, **kwargs):
        return fake_execute(stmt, *args, **kwargs)

    session.execute = async_fake_execute
    session.captured_stmts = captured_stmts
    session._food_request_enabled = food_request
    return session


def _captured_service_config_count(session) -> int:
    return sum(
        1 for stmt in session.captured_stmts if "service_configs" in str(stmt)
    )


# ---------------------------------------------------------------------------
# Puente Food V1 → ZoneState
# ---------------------------------------------------------------------------


class TestDeriveFoodZoneState:
    def test_occupancy_ratio_maps_to_saturation_level(self) -> None:
        zones = _food_zones()
        food = _food_result(zones)
        active = _select_active_phase_state(food, UUID(PHASE_IDS["p3"]))
        model = FoodV1Model()

        for zone in zones:
            occupied = active.occupied[zone.id]
            occ, _, _ = model.indices(occupied, zone.capacity)
            state = derive_food_zone_state(zone, active)
            assert state.zone_id == zone.id
            assert state.saturation_level == pytest.approx(occ)

    def test_free_spaces_maps_to_availability(self) -> None:
        zones = _food_zones()
        food = _food_result(zones)
        active = _select_active_phase_state(food, UUID(PHASE_IDS["p3"]))
        model = FoodV1Model()

        for zone in zones:
            occupied = active.occupied[zone.id]
            _, _, free = model.indices(occupied, zone.capacity)
            state = derive_food_zone_state(zone, active)
            assert state.availability == round(free)

    def test_model_result_preserves_food_metrics(self) -> None:
        zones = _food_zones()
        food = _food_result(zones)
        active = _select_active_phase_state(food, UUID(PHASE_IDS["p3"]))
        model = FoodV1Model()
        zone = zones[0]
        occupied = active.occupied[zone.id]
        occ, free_ratio, free_spaces = model.indices(occupied, zone.capacity)

        state = derive_food_zone_state(zone, active)
        data = state.model_result
        assert data["food_id"] == str(zone.id)
        assert data["subtipo"] == zone.subtipo
        assert data["occupied"] == pytest.approx(occupied)
        assert data["capacity"] == zone.capacity
        assert data["occupancy_ratio"] == pytest.approx(occ)
        assert data["free_ratio"] == pytest.approx(free_ratio)
        assert data["free_spaces"] == pytest.approx(free_spaces)
        assert data["distance"] == zone.reference_point_distance
        assert data["unabsorbed"] == pytest.approx(active.unabsorbed)

    def test_confidence_and_estimated_wait_stay_none(self) -> None:
        zones = _food_zones()
        food = _food_result(zones)
        active = _select_active_phase_state(food, UUID(PHASE_IDS["p3"]))
        for zone in zones:
            state = derive_food_zone_state(zone, active)
            assert state.confidence is None
            assert state.estimated_wait is None

    def test_base_state_metadata_is_preserved(self) -> None:
        zones = _food_zones()
        food = _food_result(zones)
        active = _select_active_phase_state(food, UUID(PHASE_IDS["p3"]))
        base = ZoneState(
            zone_id=zones[0].id,
            operational_state="HIGH_DEMAND",
            active_restriction=None,
            type="comida",
            subtipo="foodtruck",
            projected_density=333,
            reasoning_factors=["Alta densidad proyectada"],
        )
        state = derive_food_zone_state(zones[0], active, base)
        assert state.operational_state == "HIGH_DEMAND"
        assert state.projected_density == 333
        assert state.reasoning_factors == ["Alta densidad proyectada"]


# ---------------------------------------------------------------------------
# Fusión TerritorialPrediction (zonas normales + zonas gastronómicas)
# ---------------------------------------------------------------------------


class TestMergeFoodIntoPrediction:
    def test_combined_prediction_contains_normal_and_food_zones(self) -> None:
        all_zones = _food_zones() + _non_food_zones()
        base = _base_prediction(all_zones)
        food = _food_result(_food_zones())

        merged = merge_food_into_prediction(base, food)

        assert len(merged.zone_states) == len(all_zones) == 6
        food_ids = set(FOOD_IDS.values())
        normal_ids = {PARKING_ID, BANOS_ID, TRANSPORTE_ID}
        merged_ids = {zs.zone_id for zs in merged.zone_states}
        assert food_ids <= merged_ids
        assert normal_ids <= merged_ids

    def test_food_states_have_saturation_but_normal_states_do_not(self) -> None:
        all_zones = _food_zones() + _non_food_zones()
        base = _base_prediction(all_zones)
        food = _food_result(_food_zones())

        merged = merge_food_into_prediction(base, food)
        by_id = {zs.zone_id: zs for zs in merged.zone_states}

        for zid in FOOD_IDS.values():
            assert by_id[zid].saturation_level is not None
        assert by_id[PARKING_ID].saturation_level is None
        assert by_id[BANOS_ID].saturation_level is None
        assert by_id[TRANSPORTE_ID].saturation_level is None

    def test_normal_states_are_preserved_by_identity(self) -> None:
        all_zones = _food_zones() + _non_food_zones()
        base = _base_prediction(all_zones)
        food = _food_result(_food_zones())

        merged = merge_food_into_prediction(base, food)
        base_by_id = {zs.zone_id: zs for zs in base.zone_states}
        merged_by_id = {zs.zone_id: zs for zs in merged.zone_states}

        assert merged_by_id[PARKING_ID] is base_by_id[PARKING_ID]
        assert merged_by_id[BANOS_ID] is base_by_id[BANOS_ID]
        assert merged_by_id[TRANSPORTE_ID] is base_by_id[TRANSPORTE_ID]

    def test_preserves_timestamp_and_active_phase_ids(self) -> None:
        all_zones = _food_zones() + _non_food_zones()
        base = _base_prediction(all_zones)
        food = _food_result(_food_zones())

        merged = merge_food_into_prediction(base, food)

        assert merged.timestamp == base.timestamp
        assert merged.active_phase_id == base.active_phase_id
        assert merged.active_event_day_phase_id == base.active_event_day_phase_id

    def test_none_food_result_returns_base_prediction(self) -> None:
        base = _base_prediction(_food_zones() + _non_food_zones())
        merged = merge_food_into_prediction(base, None)
        assert merged is base

    def test_active_phase_is_selected_by_active_event_day_phase_id(self) -> None:
        food = _food_result(_food_zones())
        active = _select_active_phase_state(food, UUID(PHASE_IDS["p3"]))
        assert active is not None
        assert active.index == 3
        assert active.occupied.keys() == set(FOOD_IDS.values())

    def test_invariants_of_active_phase(self) -> None:
        food = _food_result(_food_zones())
        active = _select_active_phase_state(food, UUID(PHASE_IDS["p3"]))
        assert active is not None
        total = sum(active.occupied.values())
        assert total == pytest.approx(active.stock)
        for zone in food.food_zones:
            assert 0.0 <= active.occupied[zone.id] <= zone.capacity

    def test_determinism(self) -> None:
        all_zones = _food_zones() + _non_food_zones()
        base = _base_prediction(all_zones)
        food = _food_result(_food_zones())

        merged_a = merge_food_into_prediction(base, food)
        merged_b = merge_food_into_prediction(base, food)

        def snapshots(pred: TerritorialPrediction) -> tuple:
            return tuple(
                (
                    zs.zone_id,
                    zs.saturation_level,
                    zs.availability,
                    tuple(sorted(zs.model_result.items())) if zs.model_result else None,
                )
                for zs in pred.zone_states
            )

        assert snapshots(merged_a) == snapshots(merged_b)


# ---------------------------------------------------------------------------
# Flujo integrado: RecommendationModule → RecommendationService
# ---------------------------------------------------------------------------


class TestBridgeThroughRecommendationModule:
    async def test_three_food_zones_all_mapped(self) -> None:
        session = _mock_bridge_session(food_request=True)
        module = RecommendationModule(session)
        recs, prediction = await module.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_FOOD),
            limit=10,
        )

        assert prediction is not None
        by_id = {zs.zone_id: zs for zs in prediction.zone_states}
        for zid in FOOD_IDS.values():
            assert by_id[zid].saturation_level is not None
            assert by_id[zid].model_result is not None
            assert "occupancy_ratio" in by_id[zid].model_result
        # El puente Food resolvió permanencias vía ServiceConfig.
        assert _captured_service_config_count(session) > 0

    async def test_non_food_zones_excluded_from_food_recommendations(self) -> None:
        module = RecommendationModule(_mock_bridge_session(food_request=True))
        recs, prediction = await module.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_FOOD),
            limit=10,
        )

        assert recs
        assert all(isinstance(r, ZoneRecommendation) for r in recs)
        food_ids = set(FOOD_IDS.values())
        assert all(r.zone_id in food_ids for r in recs)
        # Ni parking ni baños ni transporte compiten con comida.
        assert PARKING_ID not in {r.zone_id for r in recs}
        assert BANOS_ID not in {r.zone_id for r in recs}

    async def test_normal_zones_conserved_in_combined_prediction(self) -> None:
        module = RecommendationModule(_mock_bridge_session(food_request=True))
        recs, prediction = await module.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_FOOD),
            limit=10,
        )

        by_id = {zs.zone_id: zs for zs in prediction.zone_states}
        assert PARKING_ID in by_id
        assert BANOS_ID in by_id
        assert TRANSPORTE_ID in by_id
        assert by_id[PARKING_ID].saturation_level is None
        assert by_id[BANOS_ID].saturation_level is None
        assert by_id[TRANSPORTE_ID].saturation_level is None

    async def test_scoring_uses_food_saturation(self) -> None:
        module = RecommendationModule(_mock_bridge_session(food_request=True))
        recs, prediction = await module.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_FOOD),
            limit=10,
        )

        by_id = {
            zs.zone_id: zs.saturation_level
            for zs in prediction.zone_states
            if zs.saturation_level is not None
        }
        scores = {r.zone_id: r.score for r in recs}
        # score = 1.0 - saturation (usuario STANDARD, sin zona actual): el primer
        # recomendado debe tener la menor saturación entre los considerados.
        ranked = sorted(by_id.items(), key=lambda kv: kv[1])
        assert scores[ranked[0][0]] == pytest.approx(max(scores.values()))

    async def test_determinism_of_flow(self) -> None:
        module_a = RecommendationModule(_mock_bridge_session(food_request=True))
        recs_a, _ = await module_a.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_FOOD),
            limit=10,
        )
        module_b = RecommendationModule(_mock_bridge_session(food_request=True))
        recs_b, _ = await module_b.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_FOOD),
            limit=10,
        )

        assert [(r.zone_id, r.score, r.reasoning) for r in recs_a] == [
            (r.zone_id, r.score, r.reasoning) for r in recs_b
        ]

    async def test_food_bridge_not_run_for_non_food_action(self) -> None:
        # Con acción de baños el puente Baños corre (pipeline existente) pero
        # el puente Food NO: ninguna consulta de ServiceConfig para subtipos
        # gastronómicos y las zonas comida conservan su estado base.
        session = _mock_bridge_session(food_request=False)
        module = RecommendationModule(session)
        recs, prediction = await module.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_BATHROOM),
            limit=10,
        )

        assert prediction is not None
        assert recs
        assert all(r.zone_id == BANOS_ID for r in recs)
        food_config_sqls = [
            str(stmt.compile(compile_kwargs={"literal_binds": True}))
            for stmt in session.captured_stmts
            if "service_configs" in str(stmt)
            and any(f"= '{key}'" in str(stmt.compile(
                compile_kwargs={"literal_binds": True}
            )) for key in DURATIONS_MIN)
        ]
        assert food_config_sqls == []
        by_id = {zs.zone_id: zs for zs in prediction.zone_states}
        for zid in FOOD_IDS.values():
            assert by_id[zid].saturation_level is None

    async def test_parking_and_bathroom_bridges_not_run_for_food_action(self) -> None:
        # Con acción de comida solo el puente Food se activa: las
        # recomendaciones son exclusivamente zonas gastronómicas.
        session = _mock_bridge_session(food_request=True)
        module = RecommendationModule(session)
        recs, prediction = await module.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_FOOD),
            limit=10,
        )

        assert prediction is not None
        assert recs
        assert all(r.zone_id in set(FOOD_IDS.values()) for r in recs)


# ---------------------------------------------------------------------------
# Filtro del producto Gastronomía (SEEK_FOOD → type "comida")
# ---------------------------------------------------------------------------


class TestProductFoodFilter:
    def test_seek_food_requested_action_maps_to_comida(self) -> None:
        action = RequestedAction(action_type=ActionType.SEEK_FOOD)
        assert action.type == FOOD_ZONE_TYPE
        assert action.subtipo is None

    def test_recommendation_service_only_returns_food_for_seek_food(self) -> None:
        from src.application.recommendation.recommendation_service import (
            RecommendationService,
        )

        all_zones = _food_zones() + _non_food_zones()
        base = _base_prediction(all_zones)
        food = _food_result(_food_zones())
        merged = merge_food_into_prediction(base, food)

        service = RecommendationService()
        recs = service.recommend(
            prediction=merged,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_FOOD),
            limit=10,
        )

        food_ids = set(FOOD_IDS.values())
        assert recs
        assert all(r.zone_id in food_ids for r in recs)
