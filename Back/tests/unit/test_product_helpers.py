from uuid import UUID

import pytest

from app.schemas.product import ZonaEstacionamientoItem
from src.domain.entities.zone_behavior import FlowRestriction
from src.domain.recommendation.zone_recommendation import ZoneRecommendation
from src.domain.value_objects.zone_state import ZoneState
from src.interfaces.rest.product_helpers import enrich_zone


ZONE_ID = UUID("a0000000-0000-0000-0000-000000000001")


def _rec() -> ZoneRecommendation:
    return ZoneRecommendation(zone_id=ZONE_ID, score=0.5, reasoning=[])


def _zone_state_without_model() -> ZoneState:
    # Sin modelo especializado: los atributos específicos quedan en None
    # (ADR-004). No se inventa saturación/disponibilidad/espera/confianza.
    return ZoneState(
        zone_id=ZONE_ID,
        operational_state="LOW_DEMAND",
        reasoning_factors=[],
        active_restriction=FlowRestriction.OPEN,
    )


def _zone_state_with_model() -> ZoneState:
    return ZoneState(
        zone_id=ZONE_ID,
        operational_state="LOW_DEMAND",
        availability=10,
        saturation_level=0.4,
        estimated_wait=2,
        confidence=0.8,
        reasoning_factors=[],
        active_restriction=FlowRestriction.OPEN,
    )


class TestEnrichZonePreservesAbsentModelFields:
    def test_preserves_none_when_no_model_result(self) -> None:
        item = enrich_zone(
            _rec(),
            _zone_state_without_model(),
            None,
            ZonaEstacionamientoItem,
        )
        assert item.saturation_level is None
        assert item.availability is None
        assert item.estimated_wait is None
        assert item.confidence is None
        assert item.estado is None

    def test_preserves_values_when_model_result_present(self) -> None:
        item = enrich_zone(
            _rec(),
            _zone_state_with_model(),
            None,
            ZonaEstacionamientoItem,
        )
        assert item.saturation_level == 0.4
        assert item.availability == 10
        assert item.estimated_wait == 2
        assert item.confidence == 0.8
        assert item.estado == "medio"

    def test_preserves_none_when_no_zone_state(self) -> None:
        item = enrich_zone(_rec(), None, None, ZonaEstacionamientoItem)
        assert item.saturation_level is None
        assert item.availability is None
        assert item.estimated_wait is None
        assert item.confidence is None
        assert item.estado is None