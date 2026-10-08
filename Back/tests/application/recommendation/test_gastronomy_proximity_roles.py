"""Gastronomía sin modelo: la selección curada ordena por cercanía real.

El módulo predictivo de comida está en pausa (falta curva de demanda), así que
las zonas de `comida` llegan sin `saturation_level` ni `model_result`. Antes de
este cambio eso producía dos fallos:

1. todas caían al `free_ratio = 0.9` sintético, así que "la que tiene más
   lugares libres" no distinguía nada y se resolvía por `zone_id`;
2. `_dist_to_reference` leía `model_result["distance"]`, que no existe sin
   modelo, así que el cuarto rol nunca se llenaba y devolvían 3 de 4.

Estos tests fijan el comportamiento correcto: 4 roles de cercanía y
`is_nearest` en la realmente más cercana.
"""
import math
from datetime import datetime
from uuid import UUID

import pytest

from src.application.recommendation.config import RecommendationConfig
from src.application.recommendation.strategy import (
    CURATED_ROLES,
    CURATED_ROLES_PROXIMITY,
    CURATED_ROLES_PROXIMITY_NO_GPS,
    FALLBACK_FREE_RATIO,
    WeightedScoringStrategy,
)
from src.domain.recommendation.mobility_context import MobilityContext
from src.domain.recommendation.requested_action import ActionType, RequestedAction
from src.domain.recommendation.user_context import AccessLevel, UserContext
from src.domain.value_objects.territorial_prediction import TerritorialPrediction
from src.domain.value_objects.zone_state import ZoneState

REF = (-34.6037, -58.3816)
USER = (-34.6030, -58.3800)

PUESTOS = [
    ("Foodtruck Oeste", -34.6040, -58.3830),
    ("Restaurante Norte", -34.6028, -58.3802),
    ("Patio de Comidas", -34.6035, -58.3815),
    ("Comida al Paso Sur", -34.6060, -58.3790),
    ("Pena Folk", -34.6029, -58.3805),
]
NOMBRES = {name: (lat, lng) for name, lat, lng in PUESTOS}
# Los id se derivan del índice para poder volver de una sugerencia a su puesto.
_COORD_POR_ID = {UUID(int=2000 + i): (lat, lng) for i, (_n, lat, lng) in enumerate(PUESTOS)}


def _coordenadas(zone_id: UUID) -> tuple[float, float]:
    return _COORD_POR_ID[zone_id]


def _hav(a, b, c, d):
    r = 6371000.0
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = math.radians(c - a), math.radians(d - b)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(x))


def _zonas_comida():
    states, coords = [], {}
    for i, (name, lat, lng) in enumerate(PUESTOS):
        z = ZoneState(
            zone_id=UUID(int=2000 + i),
            operational_state="NORMAL",
            availability=None,
            saturation_level=None,   # sin modelo -> sin saturación
            estimated_wait=None,
            confidence=None,
            reasoning_factors=[],
            active_restriction=None,
            type="comida",
            subtipo="foodtruck",
            projected_density=30,
            model_result=None,       # sin modelo -> sin distancia al epicentro
        )
        states.append(z)
        coords[z.zone_id] = (lat, lng)
    return states, coords


def _evaluate(*, with_gps=True, reference_point=REF):
    states, coords = _zonas_comida()
    mobility = MobilityContext(
        current_zone_id=None,
        speed=1.5,
        accessibility_required=False,
        latitude=USER[0] if with_gps else None,
        longitude=USER[1] if with_gps else None,
    )
    return WeightedScoringStrategy().evaluate(
        prediction=TerritorialPrediction(
            timestamp=datetime(2026, 10, 7, 20, 0),
            zone_states=states,
            active_phase_id=None,
            active_event_day_phase_id=None,
        ),
        user_context=UserContext(user_id=UUID(int=1), access_level=AccessLevel.STANDARD),
        mobility_context=mobility,
        requested_action=RequestedAction(action_type=ActionType.SEEK_FOOD),
        config=RecommendationConfig(),
        zone_coordinates=coords,
        reference_point=reference_point,
    )


class TestComidaUsaRolesPorCercania:
    def test_devuelve_cuatro_opciones(self):
        assert len(_evaluate()) == 4

    def test_no_repite_zona(self):
        recs = _evaluate()
        assert len({r.zone_id for r in recs}) == len(recs)

    def test_labels_distintos(self):
        recs = _evaluate()
        labels = [r.reasoning[0] for r in recs]
        assert len(set(labels)) == len(labels) == 4

    def test_usa_los_roles_de_cercania_no_los_de_disponibilidad(self):
        labels = {r.reasoning[0] for r in _evaluate()}
        assert labels == {label for label, _ in CURATED_ROLES_PROXIMITY}

    def test_no_afirma_disponibilidad_sin_medirla(self):
        """`free_ratio` es sintético: no se puede decir "más lugares libres"."""
        labels = " ".join(r.reasoning[0] for r in _evaluate())
        assert "lugares libres" not in labels

    def test_una_sola_marca_is_nearest(self):
        recs = _evaluate()
        assert sum(1 for r in recs if r.is_nearest) == 1

    def test_la_marcada_es_realmente_la_mas_cercana_al_usuario(self):
        recs = _evaluate()
        flagged = [r for r in recs if r.is_nearest]
        assert len(flagged) == 1
        la, lo = _coordenadas(flagged[0].zone_id)
        d_flagged = _hav(USER[0], USER[1], la, lo)
        d_min = min(_hav(USER[0], USER[1], la, lo) for _n, la, lo in PUESTOS)
        assert d_flagged == pytest.approx(d_min, rel=1e-6)

    def test_la_primera_es_la_mas_cercana_al_usuario(self):
        recs = _evaluate()
        assert recs[0].reasoning[0] == "Más cerca de vos"
        assert recs[0].is_nearest is True

    def test_la_tercera_es_la_mas_cercana_al_epicentro_no_elegida(self):
        """"Cerca del epicentro" se queda con el más cercano que no se haya
        usado ya; si el más cercano se llevó el rol de balance, baja al
        siguiente."""
        recs = _evaluate()
        assert recs[2].reasoning[0] == "Cerca del epicentro del evento"
        ya_elegidas = {r.zone_id for r in recs[:2]}
        candidatos = [
            (_hav(REF[0], REF[1], la, lo), zid)
            for zid, (la, lo) in _COORD_POR_ID.items()
            if zid not in ya_elegidas
        ]
        d_esperada, _zid = min(candidatos)
        la, lo = _coordenadas(recs[2].zone_id)
        assert _hav(REF[0], REF[1], la, lo) == pytest.approx(d_esperada, rel=1e-6)


class TestComidaSinGps:
    def test_devuelve_cuatro_opciones(self):
        assert len(_evaluate(with_gps=False)) == 4

    def test_usa_los_roles_por_epicentro(self):
        labels = {r.reasoning[0] for r in _evaluate(with_gps=False)}
        assert labels == {label for label, _ in CURATED_ROLES_PROXIMITY_NO_GPS}

    def test_ninguna_afirma_cercania_al_usuario_sin_gps(self):
        labels = " ".join(r.reasoning[0] for r in _evaluate(with_gps=False))
        assert "cerca de vos" not in labels.lower()

    def test_ordena_por_cercania_al_epicentro(self):
        recs = _evaluate(with_gps=False)
        d_min = min(_hav(REF[0], REF[1], la, lo) for _n, la, lo in PUESTOS)
        la, lo = _coordenadas(recs[0].zone_id)
        assert _hav(REF[0], REF[1], la, lo) == pytest.approx(d_min, rel=1e-6)
        assert recs[0].reasoning[0] == "Cerca del epicentro del evento"


class TestParkingSigueConDisponibilidad:
    """El modo por cercanía no debe tocar a quienes sí tienen medición."""

    def test_roles_de_disponibilidad_no_cambian(self):
        assert CURATED_ROLES[0][0] == "Mejor opción con más lugares libres"
        assert CURATED_ROLES[2] == ("Más cerca de vos", True)

    def test_el_fallback_sigue_siendo_el_mismo_valor(self):
        assert FALLBACK_FREE_RATIO == 0.9