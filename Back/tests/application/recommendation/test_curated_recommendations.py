"""Patrón de sugerencias curadas por rol para `estacionamiento` y `servicios`.

Cubre la Fase 1 de bathrooms: `_select_curated_options` reemplaza al ranking por
score global para que dos zonas con igual saturación no se ordenen de forma
arbitraria, y cada sugerencia llega con un label que explica su rol.
"""
from datetime import datetime
from uuid import UUID

import pytest

from src.application.recommendation.config import RecommendationConfig
from src.application.recommendation.strategy import (
    CURATED_MAX,
    CURATED_ROLES,
    CURATED_TYPES,
    WeightedScoringStrategy,
)
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import ActionType, RequestedAction
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState

# Siete baños con capacidades distintas, como el caso real reportado: cinco de
# 50 y dos de 30. Con el ranking por score devolvía las 7; el set curado debe
# devolver 4.
BATHROOM_DEFS = [
    ("Banos Delfin Diaz", 50, 0.14, 120.0),
    ("Banos Dona Pipa", 50, 0.18, 300.0),
    ("Banos Ferrocarril", 50, 0.20, 60.0),
    ("Banos Lateral Doma", 30, 0.36, 900.0),
    ("Banos Norte", 50, 0.21, 150.0),
    ("Banos Sector Este", 30, 0.33, 240.0),
    ("Banos Sur", 50, 0.19, 80.0),
]

BATHROOM_IDS = {
    name: UUID(f"b0000000-0000-0000-0000-{i:012d}")
    for i, (name, *_rest) in enumerate(BATHROOM_DEFS, start=1)
}

PARKING_DEFS = [
    ("Parking A", 3500, 0.10, 100.0),
    ("Parking B", 2800, 0.15, 220.0),
    ("Parking C", 2100, 0.20, 60.0),
    ("Parking D", 1400, 0.25, 400.0),
    ("Parking F", 1750, 0.30, 150.0),
    ("Parking G", 1050, 0.35, 90.0),
]

REF_LAT = -34.6037
REF_LNG = -58.3816


def _zone_state(name, capacity, saturation, distance):
    return ZoneState(
        zone_id=BATHROOM_IDS.get(name) or UUID(int=abs(hash(name)) % (10**12)),
        operational_state="NORMAL",
        availability=int(round(capacity * (1.0 - saturation))),
        saturation_level=saturation,
        estimated_wait=None,
        confidence=None,
        reasoning_factors=[],
        active_restriction=None,
        type="servicios" if name.startswith("Banos") else "estacionamiento",
        subtipo="banos" if name.startswith("Banos") else None,
        projected_density=int(capacity * saturation),
        model_result={
            "capacity": capacity,
            "distance": distance,
            "occupied": capacity * saturation,
        },
    )


@pytest.fixture
def config() -> RecommendationConfig:
    return RecommendationConfig()


@pytest.fixture
def user_context() -> UserContext:
    return UserContext(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        access_level=AccessLevel.STANDARD,
    )


def _bathroom_prediction() -> TerritorialPrediction:
    states = [_zone_state(*d) for d in BATHROOM_DEFS]
    return TerritorialPrediction(
        timestamp=datetime(2026, 10, 7, 20, 0),
        zone_states=states,
        active_phase_id=None,
        active_event_day_phase_id=None,
    )


def _user_near_bathrooms() -> MobilityContext:
    return MobilityContext(
        current_zone_id=None,
        speed=1.5,
        accessibility_required=False,
        latitude=REF_LAT + 0.0005,
        longitude=REF_LNG + 0.0005,
    )


def _evaluate_bathrooms(config, user_context, mobility):
    return WeightedScoringStrategy().evaluate(
        prediction=_bathroom_prediction(),
        user_context=user_context,
        mobility_context=mobility,
        requested_action=RequestedAction(action_type=ActionType.SEEK_BATHROOM),
        config=config,
        zone_coordinates={
            BATHROOM_IDS[n]: (REF_LAT, REF_LNG) for n, *_ in BATHROOM_DEFS
        },
    )


class TestServiciosUsaSeleccionCurada:
    def test_servicios_esta_en_los_tipos_curados(self) -> None:
        assert "servicios" in CURATED_TYPES

    def test_parking_sigue_en_los_tipos_curados(self) -> None:
        assert "estacionamiento" in CURATED_TYPES

    def test_comida_sigue_en_los_tipos_curados(self) -> None:
        assert "comida" in CURATED_TYPES

    def test_baños_devuelve_maximo_cuatro_sugerencias(self, config, user_context) -> None:
        recs = _evaluate_bathrooms(config, user_context, _user_near_bathrooms())
        assert len(recs) == CURATED_MAX == 4
        assert len(recs) < len(BATHROOM_DEFS)

    def test_cada_sugerencia_tiene_un_label_distinto(self, config, user_context) -> None:
        recs = _evaluate_bathrooms(config, user_context, _user_near_bathrooms())
        firsts = [r.reasoning[0] for r in recs]
        assert len(set(firsts)) == len(firsts) == 4
        assert set(firsts) == {label for label, _ in CURATED_ROLES}

    def test_opcion_mas_lugares_libres_es_la_menos_saturada(
        self, config, user_context
    ) -> None:
        recs = _evaluate_bathrooms(config, user_context, _user_near_bathrooms())
        least_saturated = min(d[2] for d in BATHROOM_DEFS)
        expected = next(n for n, _c, s, _d in BATHROOM_DEFS if s == least_saturated)
        assert recs[0].zone_id == BATHROOM_IDS[expected]
        assert recs[0].reasoning[0] == "Mejor opción con más lugares libres"

    def test_solo_una_sugerencia_marca_is_nearest(self, config, user_context) -> None:
        recs = _evaluate_bathrooms(config, user_context, _user_near_bathrooms())
        assert sum(1 for r in recs if r.is_nearest) == 1

    def test_la_marcada_como_nearest_es_la_tercera_opcion(
        self, config, user_context
    ) -> None:
        recs = _evaluate_bathrooms(config, user_context, _user_near_bathrooms())
        flagged = [r for r in recs if r.is_nearest]
        assert len(flagged) == 1
        assert flagged[0].reasoning[0] == "Más cerca de vos"

    def test_zonas_no_duplicadas(self, config, user_context) -> None:
        recs = _evaluate_bathrooms(config, user_context, _user_near_bathrooms())
        assert len({r.zone_id for r in recs}) == len(recs)


class TestParkingNoSeRompe:
    def _parking_recs(self, config, user_context):
        states = [
            ZoneState(
                zone_id=UUID(f"a0000000-0000-0000-0000-{i:012d}"),
                operational_state="NORMAL",
                availability=int(round(cap * (1.0 - sat))),
                saturation_level=sat,
                estimated_wait=None,
                confidence=None,
                reasoning_factors=[],
                active_restriction=None,
                type="estacionamiento",
                subtipo=None,
                projected_density=int(cap * sat),
                model_result={"capacity": cap, "distance": d},
            )
            for i, (_n, cap, sat, d) in enumerate(PARKING_DEFS, start=1)
        ]
        coords = {
            UUID(f"a0000000-0000-0000-0000-{i:012d}"): (REF_LAT, REF_LNG)
            for i in range(1, len(PARKING_DEFS) + 1)
        }
        return WeightedScoringStrategy().evaluate(
            prediction=TerritorialPrediction(
                timestamp=datetime(2026, 10, 7, 20, 0),
                zone_states=states,
                active_phase_id=None,
                active_event_day_phase_id=None,
            ),
            user_context=user_context,
            mobility_context=MobilityContext(
                current_zone_id=None,
                speed=1.5,
                accessibility_required=False,
                latitude=REF_LAT + 0.0005,
                longitude=REF_LNG + 0.0005,
            ),
            requested_action=RequestedAction(action_type=ActionType.SEEK_PARKING),
            config=config,
            zone_coordinates=coords,
        )

    def test_parking_sigue_devolviendo_cuatro(self, config, user_context) -> None:
        assert len(self._parking_recs(config, user_context)) == 4

    def test_parking_conserva_los_cuatro_labels(self, config, user_context) -> None:
        recs = self._parking_recs(config, user_context)
        assert [r.reasoning[0] for r in recs] == [l for l, _ in CURATED_ROLES]


class TestTruncadoPorMaxRecommendations:
    def _call(self, config, user_context, max_recommendations):
        return WeightedScoringStrategy._select_curated_options(
            [_zone_state(*d) for d in BATHROOM_DEFS],
            user_context,
            _user_near_bathrooms(),
            config,
            {
                BATHROOM_IDS[n]: (REF_LAT, REF_LNG)
                for n, *_ in BATHROOM_DEFS
            },
            max_recommendations=max_recommendations,
        )

    def test_max_menor_que_cuatro_trunca(self, config, user_context) -> None:
        for n in (0, 1, 2, 3):
            recs = self._call(config, user_context, n)
            assert len(recs) == n

    def test_max_mayor_que_cuatro_no_agrega_roles(
        self, config, user_context
    ) -> None:
        assert len(self._call(config, user_context, 10)) == CURATED_MAX

    def test_truncar_conserva_los_labels_de_los_roles_mantenidos(
        self, config, user_context
    ) -> None:
        recs = self._call(config, user_context, 2)
        assert [r.reasoning[0] for r in recs] == [
            l for l, _ in CURATED_ROLES[:2]
        ]