"""Tests del rate limiting de las rutas públicas.

Dos capas:

1. `TestInMemorySlidingWindowBackend` prueba el algoritmo con un reloj
   inyectado, sin HTTP y sin esperar de verdad.
2. Las clases que terminan en `Test...PublicRoutes` peganle a la app con
   `TestClient` y comprueban el contrato observable: 200 hasta el limite, 429 con
   `Retry-After` y el cuerpo acordado.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from src.infrastructure.middleware import rate_limit as rl
from src.infrastructure.middleware.rate_limit import (
    IN_MEMORY_WARNING,
    LOGIN_LIMIT,
    PUBLIC_READ_LIMIT,
    PUBLIC_WRITE_LIMIT,
    InMemorySlidingWindowBackend,
    RateLimitBackend,
    RateLimitDecision,
    RedisSlidingWindowBackend,
    get_backend,
    rate_limit,
    reset_backend,
    resolve_client_ip,
    set_backend,
)

EVENT_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "550e8400-e29b-41d4-a716-446655440000"


class FakeClock:
    """Reloj monotónico Falseable para probar el vencimiento de la ventana."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def backend(clock: FakeClock) -> InMemorySlidingWindowBackend:
    b = InMemorySlidingWindowBackend(now_fn=clock)
    set_backend(b)
    yield b
    set_backend(None)


@pytest.fixture
def client(test_engine) -> TestClient:
    """Cliente con backend limpio por test, sin depender del orden.

    `test_engine` (y el override de `get_db`) es necesario desde que el login
    consulta la tabla `users`: antes comparaba `admin`/`1234` en memoria y no
    tocaba la base, así que este módulo podía correr sin Postgres detrás. Ahora,
    sin el override, el login abriría el motor real de `settings.DATABASE_URL` —
    la de desarrollo— y el test fallaría por conexión, no por rate limit.
    """
    set_backend(InMemorySlidingWindowBackend())

    def override_get_db():
        with Session(bind=test_engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db, None)
        set_backend(None)


# ── Algoritmo: ventana deslizante ──────────────────────────────────────────


class TestInMemorySlidingWindowBackend:
    async def test_allows_up_to_the_limit(self, backend):
        for i in range(5):
            decision = await backend.hit("k", limit=5, window=60)
            assert decision.allowed, f"golpe {i + 1} deberia pasar"
            assert decision.count == i + 1

    async def test_blocks_the_first_one_over_the_limit(self, backend):
        for _ in range(5):
            await backend.hit("k", limit=5, window=60)

        decision = await backend.hit("k", limit=5, window=60)

        assert decision.allowed is False
        assert decision.count == 6

    async def test_keys_are_independent(self, backend):
        for _ in range(5):
            await backend.hit("k1", limit=5, window=60)

        decision = await backend.hit("k2", limit=5, window=60)

        assert decision.allowed is True

    async def test_window_expires(self, backend, clock):
        for _ in range(5):
            await backend.hit("k", limit=5, window=60)

        clock.advance(61)

        decision = await backend.hit("k", limit=5, window=60)

        assert decision.allowed is True
        assert decision.count == 1

    async def test_it_is_sliding_not_fixed_window(self, backend, clock):
        """El cupo se repone a medida que cada golpe sale de la ventana.

        Con una ventana FIJA de 60 s, al cruzar el segundo 60 se renovaria el
        cupo entero de golpe. Con deslizante, en el mismo instante solo se repone
        lo que ya salio: un golpe por vez. Aca a las 1060 s solo vencio el golpe
        de las 1000 s, asi que se libera exactamente un lugar.
        """
        # Dos golpes alive separated: t=1000 y t=1030. Ventana de 60 s.
        assert (await backend.hit("k", limit=3, window=60)).allowed is True
        clock.advance(30)
        assert (await backend.hit("k", limit=3, window=60)).allowed is True

        clock.advance(30)  # t=1060: el golpe de t=1000 sale de la ventana
        decision = await backend.hit("k", limit=3, window=60)

        # Quedaba 1 golpe vivo (t=1030) + este = 2 de 3: se libero UN lugar.
        assert decision.count == 2
        assert decision.allowed is True

        # Y solo uno: la ventana deslizante no se "reinicia" completa.
        assert (await backend.hit("k", limit=3, window=60)).allowed is True
        assert (await backend.hit("k", limit=3, window=60)).allowed is False

    async def test_window_boundary_is_exclusive(self, backend, clock):
        """Un golpe de hace exactamente `window` segundos ya esta vencido."""
        for _ in range(5):
            await backend.hit("k", limit=5, window=60)

        clock.advance(60)

        decision = await backend.hit("k", limit=5, window=60)
        assert decision.count == 1

    async def test_reset_clears_all_state(self, backend):
        for _ in range(5):
            await backend.hit("k", limit=5, window=60)
        assert (await backend.hit("k", limit=5, window=60)).allowed is False

        await backend.reset()

        assert (await backend.hit("k", limit=5, window=60)).allowed is True

    async def test_reset_after_cleared_key_does_not_resurrect_it(self, backend):
        for _ in range(3):
            await backend.hit("k", limit=3, window=60)
        await backend.reset()

        assert (await backend.hit("k", limit=3, window=60)).count == 1

    async def test_remaining_never_goes_negative(self, backend):
        for _ in range(9):
            await backend.hit("k", limit=5, window=60)

        decision = await backend.hit("k", limit=5, window=60)

        assert decision.remaining == 0

    async def test_reset_after_is_positive_when_blocked(self, backend, clock):
        for _ in range(5):
            await backend.hit("k", limit=5, window=60)
        decision = await backend.hit("k", limit=5, window=60)

        assert decision.allowed is False
        assert decision.reset_after >= 1
        assert decision.reset_after <= 60


# ── Resolución de IP ───────────────────────────────────────────────────────


class TestResolveClientIp:
    def _request(self, headers: dict, client_host: str | None = "10.0.0.1"):
        from starlette.datastructures import Headers

        class _Client:
            host = client_host

        scope = {
            "type": "http",
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
            "client": (_Client.host, 1234) if client_host else None,
        }
        from fastapi import Request

        return Request(scope)

    def test_prefers_x_forwarded_for(self):
        request = self._request({"x-forwarded-for": "203.0.113.9, 10.1.1.1"})
        assert resolve_client_ip(request) == "203.0.113.9"

    def test_falls_back_to_request_client_host(self):
        request = self._request({}, client_host="198.51.100.7")
        assert resolve_client_ip(request) == "198.51.100.7"

    def test_unknown_without_any_source(self):
        request = self._request({}, client_host=None)
        assert resolve_client_ip(request) == "unknown"

    def test_handles_missing_request(self):
        assert resolve_client_ip(None) == "unknown"

    def test_ignores_empty_forwarded_header(self):
        request = self._request({"x-forwarded-for": "  "}, client_host="192.0.2.1")
        assert resolve_client_ip(request) == "192.0.2.1"


# ── Selección de backend ───────────────────────────────────────────────────


class TestBackendSelection:
    async def test_falls_back_to_memory_without_redis_installed(
        self, monkeypatch, caplog
    ):
        set_backend(None)
        monkeypatch.setattr(settings, "REDIS_URL", "redis://localhost:6379/0")

        with caplog.at_level("WARNING"):
            chosen = await get_backend()

        assert isinstance(chosen, InMemorySlidingWindowBackend)
        set_backend(None)

    async def test_degrades_when_redis_ping_fails(self, monkeypatch):
        """Un Redis configurado pero caido no debe tumbar los endpoints."""
        set_backend(None)
        monkeypatch.setattr(settings, "REDIS_URL", "redis://localhost:6379/0")

        async def boom():
            raise ConnectionError("redis caido")

        monkeypatch.setattr(RedisSlidingWindowBackend, "ping", boom)

        chosen = await get_backend()

        assert isinstance(chosen, InMemorySlidingWindowBackend)
        set_backend(None)

    async def test_uses_redis_when_ping_succeeds(self, monkeypatch):
        set_backend(None)
        monkeypatch.setattr(settings, "REDIS_URL", "redis://localhost:6379/0")

        async def ok(self=None):
            return True

        monkeypatch.setattr(RedisSlidingWindowBackend, "ping", ok)

        chosen = await get_backend()

        assert isinstance(chosen, RedisSlidingWindowBackend)
        set_backend(None)

    def test_in_memory_warning_text(self):
        """El texto del warning es el pactado con quien pidió el fallback."""
        assert "in-memory fallback" in IN_MEMORY_WARNING
        assert "Redis" in IN_MEMORY_WARNING

    def test_redis_backend_defers_the_import(self):
        """`redis` no esta en requirements: el import no puede ser de modulo."""
        import inspect as _inspect

        source = _inspect.getsource(RedisSlidingWindowBackend)
        assert "from redis.asyncio import from_url" in source
        # El import tiene que estar dentro de un metodo, no al tope del modulo.
        assert source.index("from redis.asyncio") > source.index("def ")


# ── Decorador: contrato y configuracion ────────────────────────────────────


class TestRateLimitDecorator:
    def test_rejects_sync_endpoints_explicitly(self):
        @rate_limit(limit=1)
        def sync_endpoint(request=None):
            return "nunca"

        with pytest.raises(RuntimeError, match="async def"):
            sync_endpoint()

    async def test_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
        set_backend(InMemorySlidingWindowBackend())

        @rate_limit(limit=1)
        async def endpoint(request=None):
            return "ok"

        for _ in range(5):
            assert await endpoint() == "ok"

    def test_preserves_the_endpoint_name(self):
        @rate_limit(limit=1)
        async def endpoint(request=None):
            return "ok"

        assert endpoint.__name__ == "endpoint"

    def test_auto_injects_request_when_absent(self):
        """Un endpoint sin `request: Request` sigue recibiendo la IP."""

        @rate_limit(limit=1)
        async def endpoint(x: int = 1):
            return x

        assert "request" in endpoint.__signature__.parameters


# ── Contrato HTTP sobre la app ─────────────────────────────────────────────


class TestPublicReadRoutesRateLimit:
    """Los GET publicos permiten 60 por minuto y despues cortan con 429."""

    def _url(self, product: str) -> str:
        return (
            f"/api/events/{EVENT_ID}/products/{product}"
            "?speed=1.5&accessibility_required=false"
            f"&user_id={USER_ID}"
        )

    def test_products_allow_up_to_the_limit(
        self, client: TestClient, backend: RateLimitBackend
    ):
        from app.schemas.product import BathroomRecommendationResponse

        with patch_adapter("bathroom", zonas=[]):
            statuses = [
                client.get(self._url("bathroom")).status_code
                for _ in range(PUBLIC_READ_LIMIT)
            ]

        assert statuses == [200] * PUBLIC_READ_LIMIT

    def test_the_request_over_the_limit_is_rejected(
        self, client: TestClient, backend: RateLimitBackend
    ):
        with patch_adapter("bathroom", zonas=[]):
            for _ in range(PUBLIC_READ_LIMIT):
                client.get(self._url("bathroom"))
            resp = client.get(self._url("bathroom"))

        assert resp.status_code == 429
        assert resp.json() == {"error": "Rate limit exceeded", "retry_after": 60}

    def test_429_carries_retry_after_header(
        self, client: TestClient, backend: RateLimitBackend
    ):
        with patch_adapter("bathroom", zonas=[]):
            for _ in range(PUBLIC_READ_LIMIT):
                client.get(self._url("bathroom"))
            resp = client.get(self._url("bathroom"))

        assert resp.headers["Retry-After"] == "60"
        assert resp.headers["X-RateLimit-Limit"] == str(PUBLIC_READ_LIMIT)
        assert resp.headers["X-RateLimit-Remaining"] == "0"

    def test_the_limit_is_per_endpoint(self, client: TestClient, backend):
        """Agotar productos/bathroom no debe cerrar /products/parking."""
        with patch_adapter("bathroom", zonas=[]):
            for _ in range(PUBLIC_READ_LIMIT):
                client.get(self._url("bathroom"))

        with patch_adapter("parking", zonas=[]):
            assert client.get(self._url("parking")).status_code == 200

    def test_the_limit_is_per_ip(self, client: TestClient, backend, clock):
        """Una IP no puede agotar el cupo de otra."""
        with patch_adapter("bathroom", zonas=[]):
            for _ in range(PUBLIC_READ_LIMIT):
                client.get(
                    self._url("bathroom"), headers={"X-Forwarded-For": "203.0.113.1"}
                )
            agotada = client.get(
                self._url("bathroom"), headers={"X-Forwarded-For": "203.0.113.1"}
            )
            otra = client.get(
                self._url("bathroom"), headers={"X-Forwarded-For": "203.0.113.2"}
            )

        assert agotada.status_code == 429
        assert otra.status_code == 200

    def test_abuse_is_logged_for_monitoring(
        self, client: TestClient, backend, caplog
    ):
        """Cada 429 deja rastro: endpoint, IP y limite, para poder alertar."""
        with caplog.at_level("WARNING", logger="src.infrastructure.middleware.rate_limit"):
            with patch_adapter("bathroom", zonas=[]):
                for _ in range(PUBLIC_READ_LIMIT):
                    client.get(
                        self._url("bathroom"),
                        headers={"X-Forwarded-For": "203.0.113.5"},
                    )
                client.get(
                    self._url("bathroom"),
                    headers={"X-Forwarded-For": "203.0.113.5"},
                )

        registro = next(
            r for r in caplog.records if "Rate limit exceeded" in r.getMessage()
        )
        message = registro.getMessage()
        assert "203.0.113.5" in message
        assert "/products/bathroom" in message
        assert f"limit={PUBLIC_READ_LIMIT}" in message


class TestActivityWriteRateLimit:
    """POST /activity es la unica escritura publica: 10 por minuto."""

    URL = f"/api/events/{EVENT_ID}/activity"
    BODY = {"interaction_type": "screen_open", "service_category": "exit"}

    def test_allows_ten_then_blocks(self, client: TestClient, backend):
        with patch("app.api.routes.activity.log_service_interaction", new_callable=AsyncMock):
            statuses = [
                client.post(self.URL, json=self.BODY).status_code
                for _ in range(PUBLIC_WRITE_LIMIT)
            ]
            bloqueado = client.post(self.URL, json=self.BODY)

        assert statuses == [201] * PUBLIC_WRITE_LIMIT
        assert bloqueado.status_code == 429

    def test_write_limit_is_stricter_than_read(self):
        assert PUBLIC_WRITE_LIMIT < PUBLIC_READ_LIMIT


class TestLoginRateLimit:
    """POST /login es la barrera de fuerza bruta: 5 por minuto.

    Los intentos usan un usuario inexistente a proposito: asi se ejercita el
    rate limit por IP sin depender del lockout por cuenta ni de que exista un
    usuario sembrado. El login nuevo compara contra la tabla `users` y 401 es la
    respuesta tanto para "no existe" como para "contrasena mala".
    """

    URL = "/api/auth/login"
    USER = "rate-limit-probe"

    def test_allows_five_then_blocks(self, client: TestClient, backend):
        statuses = [
            client.post(
                self.URL, json={"username": self.USER, "password": "malo"}
            ).status_code
            for _ in range(LOGIN_LIMIT)
        ]
        bloqueado = client.post(
            self.URL, json={"username": self.USER, "password": "malo"}
        )

        assert statuses == [401] * LOGIN_LIMIT
        assert bloqueado.status_code == 429

    def test_the_limit_counts_every_attempt(self, client: TestClient, backend):
        """El limite es por intento, no solo por fallo.

        No se puede farmear contadores distinguendo "acierto" de "fallo": ambos
        consumen cupo. Con el login viejo (credenciales en el codigo) esto se podia
        verificar con la contrasena real; ahora alcanza con comprobar que la
        respuesta de un intento fallido tambien descuenta.
        """
        for _ in range(LOGIN_LIMIT - 1):
            client.post(self.URL, json={"username": self.USER, "password": "malo"})

        # Un intento más (el LOGIN_LIMITésimo) entra; el siguiente, no.
        dentro = client.post(
            self.URL, json={"username": self.USER, "password": "malo"}
        )
        assert dentro.status_code == 401

        bloqueado = client.post(
            self.URL, json={"username": self.USER, "password": "malo"}
        )
        assert bloqueado.status_code == 429

    def test_login_limit_is_the_strictest(self):
        assert LOGIN_LIMIT < PUBLIC_WRITE_LIMIT < PUBLIC_READ_LIMIT


def patch_adapter(module: str, zonas: list):
    """Parchea el adapter de un producto para aislar el rate limit de la logica."""
    from contextlib import contextmanager
    from datetime import datetime, timezone

    from unittest.mock import patch as _patch

    from app.schemas.product import BathroomRecommendationResponse

    @contextmanager
    def _cm():
        with _patch(
            f"app.api.routes.{module}.get_{module}_product_adapter",
            new_callable=AsyncMock,
        ) as mock:
            mock.return_value = BathroomRecommendationResponse(
                event_id=EVENT_ID,
                timestamp=datetime.now(timezone.utc).isoformat(),
                mode="sin_solucion",
                zonas=zonas,
            )
            yield mock

    return _cm()