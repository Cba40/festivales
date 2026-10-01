"""Rate limiting para las rutas públicas del Visitor App.

Problema
--------
Las rutas públicas (`/products/*`, `/predictions`, `/cities`, `/emergencies`,
`/alerts`, `/activity`, `/login`) no exigen token, asi que cualquier scraper las
puede hammering. Necesitan un tope por IP.

Limites por tipo de operacion
-----------------------------
- Lectura publica (`GET`): 60 req/min. Amplio a proposito: un usuario real
  consumiendo productos durante una jornada no llega ni a 20.
- Escritura anonima (`POST /activity`): 10 req/min. Es la unica ruta publica que
  escribe, asi que es la que mas conviene acotar (telemetría inyectada).
- Autenticacion (`POST /login`): 5 req/min. Barrera de fuerza bruta: 5 intentos
  por minuto y IP ya hunden cualquier ataque por fuerza bruta online.

Backends
--------
El limite se cuenta con un almacen compartido, no en memoria del proceso, porque
el despliegue es Vercel serverless: cada instancia replica su propio contador y
cada cold start lo reinicia, de modo que un contador en memoria no limita nada
en produccion (aunque si frena el abuso basico dentro de una instancia).

`RedisSlidingWindowBackend` es el backend de produccion. `InMemorySlidingWindowBackend`
es el fallback automatico para desarrollo y tests.

COMO ACTIVAR REDIS
------------------
Sin tocar ninguna ruta ni ningun test, solo dos pasos:

1. Anadir el paquete cliente a `requirements.txt`::

       redis>=5.0

2. Definir `REDIS_URL` en el entorno (en Vercel: variable de entorno del
   proyecto). Ya hay una declarada en `Back/.env`
   (`REDIS_URL=redis://localhost:6379/0`), pero hasta ahora **ningun modulo la
   leia**: era una variable muerta.

Con `redis` importable y `REDIS_URL` apuntando a un Redis accesible, el primer
`get_backend()` hace el ping, usa Redis y lo dice en el log. Si el ping falla,
degrada a memoria y avisa. Ninguna ruta cambia de codigo en ninguno de los dos
casos.

Nota sobre el algoritmo: ventana deslizante real, no ventana fija. Con
`INCR` + `EXPIRE` (lo que suele llamar "rate limit" en Redis) el limite se
reinicia en bloque cada 60 s, asi que un cliente puede hacer 2x el limite
justo alrededor del borde. Aqui se descartan los golpes que caen fuera de la
ventana en el momento de contarlos.
"""
from __future__ import annotations

import inspect
import logging
import math
import time
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Deque, Dict, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_SECONDS = 60

#: Limites de lectura publica, en requests por minuto.
PUBLIC_READ_LIMIT = 60
#: Escritura anonima (`POST /activity`).
PUBLIC_WRITE_LIMIT = 10
#: Autenticacion (`POST /login`): barrera de fuerza bruta.
LOGIN_LIMIT = 5

IN_MEMORY_WARNING = (
    "Rate limiting using in-memory fallback (per-instance). "
    "Configure Redis for distributed rate limiting."
)

#: Cabeceras que usan los proxies (Vercel, nginx) para publicar la IP real.
_FORWARDED_IP_HEADERS = ("x-forwarded-for", "x-real-ip", "cf-connecting-ip")


@dataclass(frozen=True)
class RateLimitDecision:
    """Resultado de registrar un golpe contra el limite de ``key``."""

    allowed: bool
    limit: int
    window: int
    count: int
    reset_after: int

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.count)


class RateLimitBackend(ABC):
    """Almacen compartido de golpes por clave, con ventana deslizante."""

    @abstractmethod
    async def hit(self, key: str, limit: int, window: int) -> RateLimitDecision:
        """Registra un golpe y devuelve si esta dentro del limite."""

    @abstractmethod
    async def reset(self) -> None:
        """Borra todo el estado. Lo usan los tests para no depender del orden."""


class InMemorySlidingWindowBackend(RateLimitBackend):
    """Ventana deslizante en memoria del proceso.

    Preciso (guarda el instante exacto de cada golpe), pero el estado no se
    comparte entre instancias ni sobrevive a un cold start. Es el fallback de
    desarrollo y el backend que usan los tests.

    `now_fn` existe para que los tests puedan avanzar el reloj y comprobar el
    vencimiento de la ventana sin dormir de verdad.
    """

    def __init__(self, now_fn: Callable[[], float] = time.monotonic) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._now_fn = now_fn

    async def hit(self, key: str, limit: int, window: int) -> RateLimitDecision:
        now = self._now_fn()
        self._prune(now, window)

        hits = self._hits[key]
        hits.append(now)

        # `Retry-After` es "en cuantos segundos podes reintentar", o sea cuando
        # sale de la ventana el golpe mas viejo. Con la ventana de 60 s y un golpe
        # de hace 0 s, la respuesta correcta es 60, no 61.
        oldest_age = now - hits[0]
        reset_after = max(1, math.ceil(window - oldest_age))

        return RateLimitDecision(
            allowed=len(hits) <= limit,
            limit=limit,
            window=window,
            count=len(hits),
            reset_after=reset_after,
        )

    def _prune(self, now: float, window: int) -> None:
        """Descarta golpes viejos. Barato de hacer en cada hit: `deque` es O(1)."""
        cutoff = now - window
        for key in list(self._hits):
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if not hits:
                del self._hits[key]

    async def reset(self) -> None:
        self._hits.clear()


class RedisSlidingWindowBackend(RateLimitBackend):
    """Ventana deslizante sobre Redis con un Sorted Set por clave.

    Cada golpe es un miembro del ZSET con su marca de tiempo en milisegundos.
    Antes de contar se descartan los miembros mas viejos que la ventana
    (`ZREMRANGEBYSCORE`), y luego se cuenta (`ZCARD`). Eso es una ventana
    deslizante real y no una ventana fija.

    La importacion de ``redis`` es perezosa a proposito: el paquete es opcional
    y el build de Vercel no debe romperse si todavia no esta en
    `requirements.txt`.
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._client: Any = None

    async def _get_client(self) -> Any:
        if self._client is None:
            from redis.asyncio import from_url  # Import perezoso y opcional.

            self._client = from_url(self._url, decode_responses=True)
        return self._client

    async def ping(self) -> bool:
        client = await self._get_client()
        return bool(await client.ping())

    async def hit(self, key: str, limit: int, window: int) -> RateLimitDecision:
        client = await self._get_client()
        now_ms = int(time.time() * 1000)
        window_ms = window * 1000

        pipe = client.pipeline(transaction=True)
        pipe.zremrangebyscore(key, 0, now_ms - window_ms)
        # El miembro necesita ser unico: dos golpes en el mismo milisegundo
        # colapsarian en un solo miembro del ZSET y el conteo seria erroneo.
        pipe.zadd(key, {f"{now_ms}-{uuid.uuid4().hex}": now_ms})
        pipe.zcard(key)
        pipe.pttl(key)
        _, _, count, ttl_ms = await pipe.execute()

        count = int(count)
        if ttl_ms and ttl_ms > 0:
            # Mismo criterio que el backend en memoria: segundos que faltan para
            # que el miembro mas viejo salga de la ventana, redondeado hacia arriba
            # y con un piso de 1 (un `Retry-After: 0` invita a reintentar ya).
            reset_after = max(1, math.ceil(ttl_ms / 1000))
        else:
            reset_after = window
            await client.expire(key, window)

        return RateLimitDecision(
            allowed=count <= limit,
            limit=limit,
            window=window,
            count=count,
            reset_after=reset_after,
        )

    async def reset(self) -> None:
        client = await self._get_client()
        await client.flushdb()


_backend: Optional[RateLimitBackend] = None
_warned_in_memory = False


def _settings_redis_url() -> Optional[str]:
    """`REDIS_URL` de la configuracion, o `None` si no esta definida.

    Se lee de forma perezosa y tolerante: `src/` no debe romperse si la
    configuracion de `app/` cambia de forma.
    """
    try:
        from app.core.config import settings

        url = getattr(settings, "REDIS_URL", None)
    except Exception:  # pragma: no cover - configuracion inservible
        return None
    return url or None


async def get_backend() -> RateLimitBackend:
    """Devuelve el backend compartido, eligiendo Redis si esta disponible.

    Se resuelve una sola vez por proceso. Con `redis` importable y `REDIS_URL`
    alcanzable usa Redis; en cualquier otro caso degrada a memoria y avisa una
    sola vez con `IN_MEMORY_WARNING`.
    """
    global _backend, _warned_in_memory

    if _backend is not None:
        return _backend

    url = _settings_redis_url()
    if url:
        try:
            candidate = RedisSlidingWindowBackend(url)
            if await candidate.ping():
                _backend = candidate
                logger.info(
                    "Rate limiting using Redis (distributed). url=%s", url.split("@")[-1],
                )
                return _backend
            logger.warning("REDIS_URL responde pero el ping no es PONG; degrado a memoria.")
        except Exception as exc:
            logger.warning(
                "Redis no disponible (%s: %s); degrado al fallback en memoria.",
                type(exc).__name__,
                exc,
            )

    if not _warned_in_memory:
        logger.warning(IN_MEMORY_WARNING)
        _warned_in_memory = True

    _backend = InMemorySlidingWindowBackend()
    return _backend


def set_backend(backend: Optional[RateLimitBackend]) -> None:
    """Fuerza el backend. Lo usan los tests; en produccion no hace falta."""
    global _backend, _warned_in_memory
    _backend = backend
    _warned_in_memory = True


async def reset_backend() -> None:
    """Limpia el estado del backend activo (tests)."""
    if _backend is not None:
        await _backend.reset()


def resolve_client_ip(request: Optional[Request]) -> str:
    """IP real del cliente, tolerando el proxy de Vercel.

    ``request.client.host`` en Vercel es la IP del proxy, no la del visitante:
    usarla sola collapsing a un unico bucket para toda la poblacion, que es
    justo el fallo que el rate limit quiere evitar. Por eso se priorizan las
    cabeceras que agrega el proxy.
    """
    if request is None:
        return "unknown"
    for header in _FORWARDED_IP_HEADERS:
        raw = request.headers.get(header)
        if not raw:
            continue
        # X-Forwarded-For es una cadena de saltos: "cliente, proxy1, proxy2".
        candidate = raw.split(",")[0].strip()
        if candidate:
            return candidate
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


def _extract_request(args: tuple, kwargs: dict) -> Optional[Request]:
    """Localiza el `Request` entre los argumentos de la llamada.

    `functools.wraps` hace que FastAPI siga viendo la firma original del
    endpoint, asi que un parametro declarado `request: Request` lo inyecta
    FastAPI y llega aqui como kwarg.
    """
    candidate = kwargs.get("request")
    if isinstance(candidate, Request):
        return candidate
    for value in args:
        if isinstance(value, Request):
            return value
    return None


async def log_rate_limit_violation(
    endpoint: str,
    client_ip: str,
    limit: int,
    window: int,
) -> None:
    """Registra un intento de abuso para poder alertar sobre el en el log."""
    logger.warning(
        "Rate limit exceeded: endpoint=%s ip=%s limit=%d window=%ds",
        endpoint,
        client_ip,
        limit,
        window,
    )


def rate_limit(
    limit: int = PUBLIC_READ_LIMIT,
    window: int = DEFAULT_WINDOW_SECONDS,
    name: Optional[str] = None,
) -> Callable[[Callable], Callable]:
    """Limita ``limit`` requests por ``window`` segundos y por IP.

    El endpoint debe declarar ``request: Request`` en su firma: es por ahi por
    donde llega la IP, y `functools.wraps` mantiene la firma intacta para que
    FastAPI siga inyectando el resto de dependencias con normalidad.

    Cuando se excede el limite devuelve 429 con el cuerpo pedido por la API
    publica (``{"error", "retry_after"}``) y la cabecera ``Retry-After``.
    Devolver la `Response` en vez de levantar `HTTPException` es a proposito:
    el cuerpo de FastAPI seria ``{"detail": {...}}``, que no es el contrato
    acordado, y registrarla obligaria a tocar el manejador global de errores.
    """

    def decorator(func: Callable) -> Callable:
        endpoint_name = name or func.__name__

        # `functools.wraps` NO alcanza. FastAPI no solo lee la firma: ademas
        # resuelve las anotaciones que siguen siendo texto (por
        # `from __future__ import annotations`, que usan varios de estos routers)
        # con `eval` contra `call.__globals__`, y `call` aqui es el wrapper, definido
        # en este modulo. El resultado era `PydanticUserError:
        # TypeAdapter[Annotated[ForwardRef('AccessLevel'), Query(...)]] is not fully
        # defined` y un 500 en cada endpoint con anotaciones de dominio.
        #
        # Por eso se resuelve la firma del endpoint original en SU modulo y se fija
        # como `__signature__` del wrapper: FastAPI recibe anotaciones ya
        # materializadas y no necesita volver a evaluarlas.
        try:
            resolved = inspect.signature(func, eval_str=True)
        except Exception:  # pragma: no cover - anotacion no resoluble
            resolved = None
        if resolved is not None and "request" not in resolved.parameters:
            resolved = resolved.replace(
                parameters=[*resolved.parameters.values(), inspect.Parameter(
                    "request", inspect.Parameter.KEYWORD_ONLY, annotation=Request,
                )],
            )

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            request = _extract_request(args, kwargs)
            decision = await _register(endpoint_name, request, limit, window)
            if decision is not None and not decision.allowed:
                client_ip = resolve_client_ip(request)
                endpoint_path = (
                    request.url.path if request is not None else endpoint_name
                )
                await log_rate_limit_violation(
                    endpoint_path, client_ip, limit, window,
                )
                return _too_many_requests(decision)
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError(
                f"rate_limit no soporta endpoints sincronos ({func.__name__}). "
                "Declara el endpoint como `async def`."
            )

        # Un endpoint `def` sincrono corre en un threadpool sin event loop, asi que
        # no hay forma limpia de hacer I/O asincrono ahi. En vez de un
        # `asyncio.run` dentro del thread (que se rompe en cuanto la corrutina
        # toca el loop), se delega en FastAPI para que sea un error explicito y
        # temprano en vez de un fallo silencioso.
        wrapper = async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
        if resolved is not None:
            wrapper.__signature__ = resolved
        return wrapper

    return decorator


async def _register(
    endpoint_name: str,
    request: Optional[Request],
    limit: int,
    window: int,
) -> Optional[RateLimitDecision]:
    from app.core.config import settings

    if not getattr(settings, "RATE_LIMIT_ENABLED", True):
        return None

    client_ip = resolve_client_ip(request)
    endpoint_path = request.url.path if request is not None else endpoint_name
    backend = await get_backend()
    return await backend.hit(f"rate_limit:{endpoint_path}:{client_ip}", limit, window)


def _too_many_requests(decision: RateLimitDecision) -> JSONResponse:
    """Respuesta 429 con el contrato público acordado.

    Se devuelve la `Response` en vez de lanzar `HTTPException` porque el cuerpo de
    FastAPI para una excepcion seria `{"detail": {...}}`, y el Visitor App espera
    `{"error", "retry_after"}` en la raiz.
    """
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error": "Rate limit exceeded",
            "retry_after": decision.reset_after,
        },
        headers={
            "Retry-After": str(decision.reset_after),
            "X-RateLimit-Limit": str(decision.limit),
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": str(decision.reset_after),
        },
    )