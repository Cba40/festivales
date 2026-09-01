"""ETAPA 4 Baños V1 — puente Baños → ZoneState → TerritorialPrediction → Recommendation.

Verifica el flujo completo: BathroomModule (datos reales vía AsyncSession) →
BathroomV1Model → índices por zona → ZoneState (saturation_level =
occupancy_ratio, availability = round(free_spaces)) → TerritorialPrediction
combinado → RecommendationService → solo zonas de servicios/baños.

Toda la infraestructura de BD se simula con AsyncMock (mismo patrón que la
suite): no se accede a base de datos alguna ni a SQLite.
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.domain.entities.event_day_phase import EventDayPhase
from src.domain.entities.zone import Zone
from src.domain.models.bathroom_v1_model import BathroomV1Model
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import ActionType, RequestedAction
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState
from src.infrastructure.composition.bathroom_module import (
    BathroomModule,
    BathroomSimulationResult,
    _select_active_phase_state,
    derive_bathroom_zone_state,
    merge_bathroom_into_prediction,
)
from src.infrastructure.composition.recommendation_module import RecommendationModule

EVENT_ID = "event-bridge"
DAY_ID = "11111111-1111-1111-1111-111111111111"
ATTENDANCE_ID = "55555555-5555-5555-5555-555555555555"
OP_ID = "99999999-0000-0000-0000-000000000001"
OP_PHASE_ID = "99999999-0000-0000-0000-000000000002"

ZT_IDS = {
    "bano": "22222222-2222-2222-2222-222222222222",
    "hidratacion": "66666666-6666-6666-6666-666666666666",
    "comida": "33333333-3333-3333-3333-333333333333",
    "transporte": "44444444-4444-4444-4444-444444444444",
}

# 6 zonas de servicios/baños (A, B, C, D, F, G) + 3 no-baños
# (comida, transporte y servicios/hidratacion).
BATHROOM_DEFS = [
    ("Banos A", "A", 3500),
    ("Banos B", "B", 2800),
    ("Banos C", "C", 2100),
    ("Banos D", "D", 1400),
    ("Banos F", "F", 1750),
    ("Banos G", "G", 1050),
]

BATHROOM_IDS = {
    letter: UUID(f"a0000000-0000-0000-0000-0000000000{i:02d}")
    for i, (_, letter, _) in enumerate(BATHROOM_DEFS, start=1)
}
COMIDA_ID = UUID("c0000000-0000-0000-0000-000000000001")
TRANSPORTE_ID = UUID("d0000000-0000-0000-0000-000000000001")
HIDRATACION_ID = UUID("e0000000-0000-0000-0000-000000000001")

PHASE_IDS = {
    "p1": "77777777-0000-0000-0000-000000000001",
    "p2": "77777777-0000-0000-0000-000000000002",
    "p3": "77777777-0000-0000-0000-000000000003",
}

REF_LAT = -31.4135
REF_LNG = -64.1811
TS = datetime(2026, 7, 15, 15, 0)

MAX_PEOPLE = 10000
DURATION_MIN = 5


def _zone(
    name: str,
    zid: str,
    zone_type: str,
    subtipo: str | None,
    capacity: int,
    distance: float,
    zt_key: str | None = None,
) -> Zone:
    return Zone(
        id=UUID(zid),
        name=name,
        zone_type_id=UUID(ZT_IDS[zt_key if zt_key is not None else zone_type]),
        capacity=capacity,
        type=zone_type,
        subtipo=subtipo,
        latitude=REF_LAT,
        longitude=REF_LNG,
        reference_point_distance=distance,
    )


def _bathroom_zones() -> list[Zone]:
    return [
        _zone(
            name,
            str(BATHROOM_IDS[letter]),
            "servicios",
            "banos",
            capacity,
            float(i) * 500.0,
            zt_key="bano",
        )
        for i, (name, letter, capacity) in enumerate(BATHROOM_DEFS)
    ]


def _non_bathroom_zones() -> list[Zone]:
    return [
        _zone("Comida Central", str(COMIDA_ID), "comida", None, 120, 800.0),
        _zone("Transporte Norte", str(TRANSPORTE_ID), "transporte", None, 60, 1200.0),
        _zone("Fuente Agua", str(HIDRATACION_ID), "servicios", "hidratacion", 150, 400.0, zt_key="hidratacion"),
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


def _bathroom_result(bathroom_zones: list[Zone]) -> BathroomSimulationResult:
    phases = _phases()
    model = BathroomV1Model()
    duration_hours = model.duration_hours(DURATION_MIN)
    phase_results = model.simulate(
        phases, bathroom_zones, MAX_PEOPLE, duration_hours
    )
    return BathroomSimulationResult(
        event_id=EVENT_ID,
        timestamp=TS,
        bathroom_zones=tuple(bathroom_zones),
        phases=phases,
        max_people=MAX_PEOPLE,
        average_duration_min=DURATION_MIN,
        duration_hours=duration_hours,
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


def _mock_bridge_session(*, bathroom_request: bool) -> AsyncMock:
    session = AsyncMock()

    zone_type_rows = [
        SimpleNamespace(slug="bano", id=ZT_IDS["bano"]),
        SimpleNamespace(slug="hidratacion", id=ZT_IDS["hidratacion"]),
        SimpleNamespace(slug="comida", id=ZT_IDS["comida"]),
        SimpleNamespace(slug="transporte", id=ZT_IDS["transporte"]),
    ]
    ref_row = SimpleNamespace(
        reference_point_latitude=REF_LAT,
        reference_point_longitude=REF_LNG,
    )
    all_zone_rows = [
        SimpleNamespace(
            id=zid,
            name=name,
            type="servicios",
            subtipo="banos",
            capacity=capacity,
            available_capacity=capacity,
            latitude=REF_LAT,
            longitude=REF_LNG,
        )
        for name, letter, capacity in BATHROOM_DEFS
        for zid in [str(BATHROOM_IDS[letter])]
    ] + [
        SimpleNamespace(
            id=str(COMIDA_ID),
            name="Comida Central",
            type="comida",
            subtipo=None,
            capacity=120,
            available_capacity=120,
            latitude=REF_LAT,
            longitude=REF_LNG,
        ),
        SimpleNamespace(
            id=str(TRANSPORTE_ID),
            name="Transporte Norte",
            type="transporte",
            subtipo=None,
            capacity=60,
            available_capacity=60,
            latitude=REF_LAT,
            longitude=REF_LNG,
        ),
        SimpleNamespace(
            id=str(HIDRATACION_ID),
            name="Fuente Agua",
            type="servicios",
            subtipo="hidratacion",
            capacity=150,
            available_capacity=150,
            latitude=REF_LAT,
            longitude=REF_LNG,
        ),
    ]
    bathroom_rows = [
        SimpleNamespace(
            id=zid,
            name=name,
            type="servicios",
            subtipo="banos",
            capacity=capacity,
            available_capacity=capacity,
            latitude=REF_LAT,
            longitude=REF_LNG,
        )
        for name, letter, capacity in BATHROOM_DEFS
        for zid in [str(BATHROOM_IDS[letter])]
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
                ("bano", 0.8),
                ("hidratacion", 0.5),
                ("comida", 0.6),
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
    service_config_row = SimpleNamespace(average_duration_min=DURATION_MIN)

    effects = [
        _scalars_result(zone_type_rows),
        _one_result(ref_row),
        _scalars_result(all_zone_rows),
        _scalars_result(behavior_rows),
        _scalar_one_result(ed_row),
        _scalar_one_result(attendance_row),
        _scalars_result(phase_rows),
        # operational_events (OperationalEventAdapter): sin eventos activos.
        _scalars_result([]),
    ]
    if bathroom_request:
        effects += [
            _scalars_result(zone_type_rows),
            _one_result(ref_row),
            _scalars_result(bathroom_rows),
            _scalar_one_result(ed_row),
            _scalar_one_result(attendance_row),
            _scalar_one_result(service_config_row),
        ]
    session.execute = AsyncMock(side_effect=effects)
    return session


# ---------------------------------------------------------------------------
# Puente Baños V1 → ZoneState
# ---------------------------------------------------------------------------


class TestDeriveBathroomZoneState:
    def test_occupancy_ratio_maps_to_saturation_level(self) -> None:
        zones = _bathroom_zones()
        bathroom = _bathroom_result(zones)
        active = _select_active_phase_state(bathroom, UUID(PHASE_IDS["p3"]))
        model = BathroomV1Model()

        for zone in zones:
            occupied = active.occupied[zone.id]
            occ, _, _ = model.indices(occupied, zone.capacity)
            state = derive_bathroom_zone_state(zone, active)
            assert state.zone_id == zone.id
            assert state.saturation_level == pytest.approx(occ)

    def test_free_spaces_maps_to_availability(self) -> None:
        zones = _bathroom_zones()
        bathroom = _bathroom_result(zones)
        active = _select_active_phase_state(bathroom, UUID(PHASE_IDS["p3"]))
        model = BathroomV1Model()

        for zone in zones:
            occupied = active.occupied[zone.id]
            _, _, free = model.indices(occupied, zone.capacity)
            state = derive_bathroom_zone_state(zone, active)
            assert state.availability == round(free)

    def test_model_result_preserves_bathroom_metrics(self) -> None:
        zones = _bathroom_zones()
        bathroom = _bathroom_result(zones)
        active = _select_active_phase_state(bathroom, UUID(PHASE_IDS["p3"]))
        model = BathroomV1Model()
        zone = zones[0]
        occupied = active.occupied[zone.id]
        occ, free_ratio, free_spaces = model.indices(occupied, zone.capacity)

        state = derive_bathroom_zone_state(zone, active)
        data = state.model_result
        assert data["bathroom_id"] == str(zone.id)
        assert data["occupied"] == pytest.approx(occupied)
        assert data["capacity"] == zone.capacity
        assert data["occupancy_ratio"] == pytest.approx(occ)
        assert data["free_ratio"] == pytest.approx(free_ratio)
        assert data["free_spaces"] == pytest.approx(free_spaces)
        assert data["distance"] == zone.reference_point_distance
        assert data["unabsorbed"] == pytest.approx(active.unabsorbed)

    def test_confidence_and_estimated_wait_stay_none(self) -> None:
        zones = _bathroom_zones()
        bathroom = _bathroom_result(zones)
        active = _select_active_phase_state(bathroom, UUID(PHASE_IDS["p3"]))
        for zone in zones:
            state = derive_bathroom_zone_state(zone, active)
            assert state.confidence is None
            assert state.estimated_wait is None

    def test_base_state_metadata_is_preserved(self) -> None:
        zones = _bathroom_zones()
        bathroom = _bathroom_result(zones)
        active = _select_active_phase_state(bathroom, UUID(PHASE_IDS["p3"]))
        base = ZoneState(
            zone_id=zones[0].id,
            operational_state="HIGH_DEMAND",
            active_restriction=None,
            type="servicios",
            subtipo="banos",
            projected_density=333,
            reasoning_factors=["Alta densidad proyectada"],
        )
        state = derive_bathroom_zone_state(zones[0], active, base)
        assert state.operational_state == "HIGH_DEMAND"
        assert state.projected_density == 333
        assert state.reasoning_factors == ["Alta densidad proyectada"]


# ---------------------------------------------------------------------------
# Fusión TerritorialPrediction (zonas normales + zonas de servicios/baños)
# ---------------------------------------------------------------------------


class TestMergeBathroomIntoPrediction:
    def test_combined_prediction_contains_normal_and_bathroom_zones(self) -> None:
        all_zones = _bathroom_zones() + _non_bathroom_zones()
        base = _base_prediction(all_zones)
        bathroom = _bathroom_result(_bathroom_zones())

        merged = merge_bathroom_into_prediction(base, bathroom)

        assert len(merged.zone_states) == len(all_zones) == 9
        bathroom_ids = set(BATHROOM_IDS.values())
        normal_ids = {COMIDA_ID, TRANSPORTE_ID, HIDRATACION_ID}
        merged_ids = {zs.zone_id for zs in merged.zone_states}
        assert bathroom_ids <= merged_ids
        assert normal_ids <= merged_ids

    def test_bathroom_states_have_saturation_but_normal_states_do_not(self) -> None:
        all_zones = _bathroom_zones() + _non_bathroom_zones()
        base = _base_prediction(all_zones)
        bathroom = _bathroom_result(_bathroom_zones())

        merged = merge_bathroom_into_prediction(base, bathroom)
        by_id = {zs.zone_id: zs for zs in merged.zone_states}

        for zid in BATHROOM_IDS.values():
            assert by_id[zid].saturation_level is not None
        assert by_id[COMIDA_ID].saturation_level is None
        assert by_id[TRANSPORTE_ID].saturation_level is None
        assert by_id[HIDRATACION_ID].saturation_level is None

    def test_normal_states_are_preserved_by_identity(self) -> None:
        all_zones = _bathroom_zones() + _non_bathroom_zones()
        base = _base_prediction(all_zones)
        bathroom = _bathroom_result(_bathroom_zones())

        merged = merge_bathroom_into_prediction(base, bathroom)
        base_by_id = {zs.zone_id: zs for zs in base.zone_states}
        merged_by_id = {zs.zone_id: zs for zs in merged.zone_states}

        assert merged_by_id[COMIDA_ID] is base_by_id[COMIDA_ID]
        assert merged_by_id[TRANSPORTE_ID] is base_by_id[TRANSPORTE_ID]
        assert merged_by_id[HIDRATACION_ID] is base_by_id[HIDRATACION_ID]

    def test_preserves_timestamp_and_active_phase_ids(self) -> None:
        all_zones = _bathroom_zones() + _non_bathroom_zones()
        base = _base_prediction(all_zones)
        bathroom = _bathroom_result(_bathroom_zones())

        merged = merge_bathroom_into_prediction(base, bathroom)

        assert merged.timestamp == base.timestamp
        assert merged.active_phase_id == base.active_phase_id
        assert merged.active_event_day_phase_id == base.active_event_day_phase_id

    def test_none_bathroom_result_returns_base_prediction(self) -> None:
        base = _base_prediction(_bathroom_zones() + _non_bathroom_zones())
        merged = merge_bathroom_into_prediction(base, None)
        assert merged is base

    def test_active_phase_is_selected_by_active_event_day_phase_id(self) -> None:
        bathroom = _bathroom_result(_bathroom_zones())
        active = _select_active_phase_state(bathroom, UUID(PHASE_IDS["p3"]))
        assert active is not None
        assert active.index == 3
        assert active.occupied.keys() == set(BATHROOM_IDS.values())

    def test_invariants_of_active_phase(self) -> None:
        bathroom = _bathroom_result(_bathroom_zones())
        active = _select_active_phase_state(bathroom, UUID(PHASE_IDS["p3"]))
        assert active is not None
        total = sum(active.occupied.values())
        assert total == pytest.approx(active.stock)
        for zone in bathroom.bathroom_zones:
            assert 0.0 <= active.occupied[zone.id] <= zone.capacity

    def test_determinism(self) -> None:
        all_zones = _bathroom_zones() + _non_bathroom_zones()
        base = _base_prediction(all_zones)
        bathroom = _bathroom_result(_bathroom_zones())

        merged_a = merge_bathroom_into_prediction(base, bathroom)
        merged_b = merge_bathroom_into_prediction(base, bathroom)

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
    async def test_six_bathroom_zones_all_mapped(self) -> None:
        module = RecommendationModule(_mock_bridge_session(bathroom_request=True))
        recs, prediction = await module.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_BATHROOM),
            limit=10,
        )

        assert prediction is not None
        by_id = {zs.zone_id: zs for zs in prediction.zone_states}
        for zid in BATHROOM_IDS.values():
            assert by_id[zid].saturation_level is not None
            assert by_id[zid].model_result is not None
            assert "occupancy_ratio" in by_id[zid].model_result

    async def test_non_bathroom_zones_excluded_from_bathroom_recommendations(self) -> None:
        module = RecommendationModule(_mock_bridge_session(bathroom_request=True))
        recs, prediction = await module.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_BATHROOM),
            limit=10,
        )

        assert recs
        assert all(isinstance(r, ZoneRecommendation) for r in recs)
        bathroom_ids = set(BATHROOM_IDS.values())
        assert all(r.zone_id in bathroom_ids for r in recs)
        # Ni siquiera la zona servicios/hidratacion compite con baños.
        assert HIDRATACION_ID not in {r.zone_id for r in recs}

    async def test_normal_zones_conserved_in_combined_prediction(self) -> None:
        module = RecommendationModule(_mock_bridge_session(bathroom_request=True))
        recs, prediction = await module.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_BATHROOM),
            limit=10,
        )

        by_id = {zs.zone_id: zs for zs in prediction.zone_states}
        assert COMIDA_ID in by_id
        assert TRANSPORTE_ID in by_id
        assert HIDRATACION_ID in by_id
        assert by_id[COMIDA_ID].saturation_level is None
        assert by_id[TRANSPORTE_ID].saturation_level is None
        assert by_id[HIDRATACION_ID].saturation_level is None

    async def test_scoring_uses_bathroom_saturation(self) -> None:
        module = RecommendationModule(_mock_bridge_session(bathroom_request=True))
        recs, prediction = await module.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_BATHROOM),
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
        module_a = RecommendationModule(_mock_bridge_session(bathroom_request=True))
        recs_a, _ = await module_a.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_BATHROOM),
            limit=10,
        )
        module_b = RecommendationModule(_mock_bridge_session(bathroom_request=True))
        recs_b, _ = await module_b.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_BATHROOM),
            limit=10,
        )

        assert [(r.zone_id, r.score, r.reasoning) for r in recs_a] == [
            (r.zone_id, r.score, r.reasoning) for r in recs_b
        ]

    async def test_bathroom_bridge_not_run_for_non_bathroom_action(self) -> None:
        # Sólo 7 respuestas: si el puente Baños se ejecutara, la sesión mock
        # se agotaría (StopIteration) y el flujo fallaría. SEEK_TRANSPORT no
        # activa puente alguno (SEEK_FOOD activa el puente Food V1).
        module = RecommendationModule(_mock_bridge_session(bathroom_request=False))
        recs, prediction = await module.execute(
            timestamp=TS,
            event_id=EVENT_ID,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_TRANSPORT),
            limit=10,
        )

        assert prediction is not None
        assert recs
        assert all(r.zone_id == TRANSPORTE_ID for r in recs)

    async def test_parking_bridge_not_run_for_bathroom_action(self) -> None:
        # Sólo 13 respuestas (7 base + 6 Baños): si el puente Parking se
        # ejecutara además, la sesión mock se agotaría y el flujo fallaría.
        module = RecommendationModule(_mock_bridge_session(bathroom_request=True))
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
        assert all(r.zone_id in set(BATHROOM_IDS.values()) for r in recs)


# ---------------------------------------------------------------------------
# Filtro del producto Baños (solo servicios + subtipo banos)
# ---------------------------------------------------------------------------


class TestProductBathroomFilter:
    def test_seek_bathroom_requested_action_maps_to_servicios_banos(self) -> None:
        action = RequestedAction(action_type=ActionType.SEEK_BATHROOM)
        assert action.type == "servicios"
        assert action.subtipo == "banos"

    def test_recommendation_service_only_returns_bathroom_for_seek_bathroom(self) -> None:
        from src.application.recommendation.recommendation_service import (
            RecommendationService,
        )

        all_zones = _bathroom_zones() + _non_bathroom_zones()
        base = _base_prediction(all_zones)
        bathroom = _bathroom_result(_bathroom_zones())
        merged = merge_bathroom_into_prediction(base, bathroom)

        service = RecommendationService()
        recs = service.recommend(
            prediction=merged,
            user_context=_user_context(),
            mobility_context=_mobility_context(),
            requested_action=RequestedAction(action_type=ActionType.SEEK_BATHROOM),
            limit=10,
        )

        bathroom_ids = set(BATHROOM_IDS.values())
        assert recs
        assert all(r.zone_id in bathroom_ids for r in recs)