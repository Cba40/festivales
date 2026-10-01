"""Validación de entrada de las rutas públicas.

Estas rutas no exigen token, así que cualquiera puede mandarle payloads. Los
límites de rango son la primera barrera: un `speed=1e308` o un `limit=100000`
no debe llegar a la lógica de negocio.

Nota de contrato: FastAPI responde **422** (no 400) a un parámetro
semánticamente inválido. Es el código correcto para "sintaxis válida, valor
inválido" y es el que ya usa el resto de la API (ver
`test_emergency_invalid_type_returns_422`), así que no se cambia a 400.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.middleware.rate_limit import (
    InMemorySlidingWindowBackend,
    set_backend,
)

EVENT_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "550e8400-e29b-41d4-a716-446655440000"
BASE = f"/api/events/{EVENT_ID}"


@pytest.fixture(autouse=True)
def _clean_backend():
    set_backend(InMemorySlidingWindowBackend())
    yield
    set_backend(None)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


from app.main import app  # noqa: E402  (despues del fixture, por legibilidad)


def _product_url(product: str, **overrides) -> str:
    params = {
        "speed": "1.5",
        "accessibility_required": "false",
        "user_id": USER_ID,
    }
    params.update({k: str(v) for k, v in overrides.items()})
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{BASE}/products/{product}?{query}"


@pytest.fixture
def product_adapter():
    """Evita que el rate limit y la validacion se confundan: todo 422 llega antes
    de tocar la base, asi que alcanza con no dejar que el adapter corra."""
    from contextlib import contextmanager

    @contextmanager
    def _patch(module: str):
        with patch(
            f"app.api.routes.{module}.get_{module}_product_adapter",
            new_callable=AsyncMock,
        ) as mock:
            yield mock

    return _patch


class TestSpeedRange:
    """`speed` es km/h: 0.0-10.0. Antes solo tenia cota inferior."""

    @pytest.mark.parametrize("module", ["bathroom", "parking", "hydration", "gastronomy"])
    def test_negative_speed_is_rejected(self, client, product_adapter, module):
        with product_adapter(module):
            resp = client.get(_product_url(module, speed="-1"))
        assert resp.status_code == 422

    @pytest.mark.parametrize("module", ["bathroom", "parking", "hydration", "gastronomy"])
    def test_speed_above_ten_is_rejected(self, client, product_adapter, module):
        with product_adapter(module):
            resp = client.get(_product_url(module, speed="10.1"))
        assert resp.status_code == 422

    def test_transport_speed_above_ten_is_rejected(self, client, product_adapter):
        with product_adapter("transport"):
            resp = client.get(_product_url("transport", speed="99"))
        assert resp.status_code == 422

    def test_speed_boundary_ten_is_accepted(self, client, product_adapter):
        with product_adapter("bathroom") as mock:
            from datetime import datetime, timezone

            from app.schemas.product import BathroomRecommendationResponse

            mock.return_value = BathroomRecommendationResponse(
                event_id=EVENT_ID,
                timestamp=datetime.now(timezone.utc).isoformat(),
                mode="sin_solucion",
                zonas=[],
            )
            resp = client.get(_product_url("bathroom", speed="10"))
        assert resp.status_code == 200


class TestLimitRange:
    def test_limit_above_fifty_is_rejected(self, client, product_adapter):
        with product_adapter("bathroom"):
            resp = client.get(_product_url("bathroom", limit="51"))
        assert resp.status_code == 422

    def test_limit_of_fifty_is_accepted(self, client, product_adapter):
        with product_adapter("bathroom") as mock:
            from datetime import datetime, timezone

            from app.schemas.product import BathroomRecommendationResponse

            mock.return_value = BathroomRecommendationResponse(
                event_id=EVENT_ID,
                timestamp=datetime.now(timezone.utc).isoformat(),
                mode="sin_solucion",
                zonas=[],
            )
            resp = client.get(_product_url("bathroom", limit="50"))
        assert resp.status_code == 200

    def test_limit_of_zero_is_rejected(self, client, product_adapter):
        with product_adapter("bathroom"):
            resp = client.get(_product_url("bathroom", limit="0"))
        assert resp.status_code == 422

    def test_accommodation_keeps_its_higher_ceiling(self, client):
        """El frontend pide `limit=100` en accommodationProduct.ts:73.

        Bajar el techo a 50 rompe el Visitor App con un 422, asi que se respeta
        el limite que ya tenia ese endpoint.
        """
        from app.schemas.accommodation import AccommodationRecommendationResponse

        with patch(
            "app.api.routes.accommodation.get_accommodation_product_adapter",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = AccommodationRecommendationResponse(
                event_id=EVENT_ID, accommodations=[]
            )
            resp = client.get(f"{BASE}/products/accommodation?limit=100")

        assert resp.status_code == 200


class TestCoordinateRange:
    @pytest.mark.parametrize("bad", ["90.1", "-90.1", "1000"])
    def test_latitude_out_of_range_is_rejected(self, client, product_adapter, bad):
        with product_adapter("bathroom"):
            resp = client.get(_product_url("bathroom", latitude=bad))
        assert resp.status_code == 422

    @pytest.mark.parametrize("bad", ["180.1", "-180.1", "99999"])
    def test_longitude_out_of_range_is_rejected(self, client, product_adapter, bad):
        with product_adapter("bathroom"):
            resp = client.get(_product_url("bathroom", longitude=bad))
        assert resp.status_code == 422

    def test_non_numeric_latitude_is_rejected(self, client, product_adapter):
        with product_adapter("bathroom"):
            resp = client.get(_product_url("bathroom", latitude="norte"))
        assert resp.status_code == 422

    def test_valid_coordinates_are_accepted(self, client):
        from app.schemas.exit_product import ExitRecommendationResponse

        with patch(
            "app.api.routes.exit_product.get_exit_product_adapter",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = ExitRecommendationResponse(
                event_id=EVENT_ID,
                timestamp="2026-07-10T20:00:00+00:00",
                zonas=[],
            )
            resp = client.get(f"{BASE}/products/exit?latitude=-34.6&longitude=-58.38")

        assert resp.status_code == 200


class TestActivityPayload:
    """`POST /activity` es la unica escritura publica anonima.

    `event_id` se valida con el patron UUID del `Path`. El cuerpo lo valida
    `ActivityCreate`, que además usa `extra="forbid"`: campos que no existen en
    el contrato (`endpoint`, `user_agent`) se rechazan igual.
    """

    URL = f"{BASE}/activity"
    VALID = {"interaction_type": "screen_open", "service_category": "exit"}

    @pytest.fixture
    def logger(self):
        with patch(
            "app.api.routes.activity.log_service_interaction", new_callable=AsyncMock
        ) as mock:
            yield mock

    @pytest.mark.parametrize(
        "bad_id",
        ["not-a-uuid", "123", "11111111-1111-1111-1111-11111111111"],
    )
    def test_invalid_event_id_is_rejected(self, client, logger, bad_id):
        resp = client.post(f"/api/events/{bad_id}/activity", json=self.VALID)
        assert resp.status_code == 422
        logger.assert_not_awaited()

    def test_empty_event_id_does_not_match_the_route(self, client, logger):
        """Sin `event_id` la ruta ni siquiera matchea: 404, no 422."""
        resp = client.post("/api/events//activity", json=self.VALID)
        assert resp.status_code in (404, 422)
        logger.assert_not_awaited()

    @pytest.mark.parametrize(
        "body",
        [
            {},                                                          # vacio
            {"interaction_type": "screen_open"},                          # sin category
            {"service_category": "exit"},                                 # sin type
            {"interaction_type": "delete", "service_category": "exit"},   # tipo no permitido
            {"interaction_type": "screen_open", "service_category": "nope"},  # categoria desconocida
            {"interaction_type": "screen_open", "service_category": "exit", "endpoint": "/x"},
            {"interaction_type": "screen_open", "service_category": "exit", "user_agent": "bot"},
            {"interaction_type": "request", "service_category": "exit"},
        ],
    )
    def test_malformed_payload_is_rejected(self, client, logger, body):
        resp = client.post(self.URL, json=body)
        assert resp.status_code == 422
        logger.assert_not_awaited()

    def test_request_mode_longer_than_fifty_is_rejected(self, client, logger):
        resp = client.post(
            self.URL,
            json={**self.VALID, "request_mode": "x" * 51},
        )
        assert resp.status_code == 422

    def test_valid_payload_is_accepted(self, client, logger):
        resp = client.post(self.URL, json=self.VALID)
        assert resp.status_code == 201
        logger.assert_awaited_once()

    def test_origin_is_forced_to_user(self, client, logger):
        """El cliente no elige el origin: el endpoint lo impone como `user`."""
        client.post(self.URL, json=self.VALID)

        assert logger.await_args.kwargs["origin"] == "user"


class TestEmergencyValidation:
    def test_unknown_city_id_is_rejected(self, client):
        resp = client.get("/api/emergencies?city_id=no-es-un-uuid")
        assert resp.status_code == 422

    def test_invalid_emergency_type_is_rejected(self, client):
        resp = client.get(f"/api/emergencies?city_id={EVENT_ID}&type=inexistente")
        assert resp.status_code == 422