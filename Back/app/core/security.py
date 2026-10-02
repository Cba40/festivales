"""Primitivas de criptografía: hashing de contraseñas y emisión/validación de JWT.

Dos decisiones que conviene tener presentes
-------------------------------------------
**argon2id, no bcrypt ni SHA.** SHA (ni MD5, ni un sha256 con salt) no sirve para
contraseñas: es rápido, y "rápido" es exactamente lo que necesita un atacante que
prueba millones de candidatos por segundo. argon2id es lento a propósito y además
usa memoria, así que el costo por intento crece con el hardware del atacante.
`argon2-cffi` lo trae con parámetros por defecto razonables; acá se suben un poco
por tratarse de un panel administrativo expuesto a internet.

**El hash se autodescribe.** El string que devuelve argon2id incluye sus propios
parámetros (m, t, p y la sal). Eso permite subir `time_cost` sin invalidar los
hashes viejos: `verify` lee los parámetros del hash que encuentra y no los del
código. Si se quisiera forzar el recoste de los hashes existentes habría que
re-hashear en el login.

Coste: argon2 con time_cost=3 y 96 MB de memoria por verificación. Es intencional:
un login es una operación cara y rara. Si alguna vez esto satura la instancia, el
knob es `LOGIN_RATE_LIMIT`/`argon2` params, no bajar el coste.
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings

# ── Contraseñas ──────────────────────────────────────────────────────────────
#
# `memory_cost` en KiB. 64 MB es el default de la library; se sube a 96 MB porque
# el login es la única operación que paga este costo y el objetivo es hacer caro el
# offline cracking de una tabla `users` filtrada.
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=96 * 1024,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Devuelve el hash argon2id de `password`.

    El string resultante es autocontenido (incluye sal y parámetros), así que no
    hace falta guardar la sal en otra columna.
    """
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifica la contraseña contra el hash. Nunca lanza; devuelve un bool.

    Un hash corrupto o de otro formato devuelve `False` en vez de propagar la
    excepción: el login compara credenciales, y que el hash esté raro no debería
    diferenciar "contraseña incorrecta" (401) de "error del servidor" (500),
    porque esa diferencia le diría a un atacante que ese usuario existe con un
    registro corrupto.
    """
    try:
        _hasher.verify(password_hash, password)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True si el hash fue hecho con parámetros más baratos que los actuales.

    Permite endurecer `time_cost`/`memory_cost` sin invalidar las contraseñas
    existentes: el usuario se re-hashea en su próximo login correcto.
    """
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def dummy_verify() -> None:
    """Gasta el mismo costo que una verificación real, contra un hash falso.

    Se invoca cuando el usuario NO existe, para que el login de un username
    inexistente tarde lo mismo que el de uno existente. Sin esto, medir la
    respuesta revelaría qué usernames están registrados: un atacante solo tiene que
    cronometrar 401s y armar el padrón sin crackear una sola contraseña.

    La excepción se traga a propósito: el objetivo es que la verificación corra y
    falle, que es exactamente lo que pasa con un usuario inexistente.
    """
    try:
        _hasher.verify(_DUMMY_HASH, "dummy")
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        pass


# Hash válido y bien formado, generado una vez con los parámetros de arriba. No
# corresponde a ninguna contraseña real; sirve solo para que `verify` ejecute el
# trabajo criptográfico completo.
_DUMMY_HASH = _hasher.hash("dummy-password-for-timing-only")


# ── Refresh tokens ───────────────────────────────────────────────────────────

def hash_token(token: str) -> str:
    """SHA-256 hex del token completo.

    Acá SÍ sirve SHA: no es un secreto adivinable por fuerza bruta, es un valor
    aleatorio de 256 bits de entropía. Lo que se protege es el contenido de la
    tabla: si alguien lee `refresh_tokens` (un dump, un backup, un log), con el
    hash no puede suplantar la sesión.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_jti() -> str:
    """Identificador único de token, para poder revocarlo individualmente."""
    return str(uuid.uuid4())


def generate_refresh_secret() -> str:
    """Secret aleatorio para el refresh token, que no es un JWT.

    Se genera por sesión y se guarda hasheado. Si fuera un JWT, el logout no
    podría invalidarlo hasta que expirara.
    """
    return secrets.token_urlsafe(48)


# ── JWT ──────────────────────────────────────────────────────────────────────

TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_REFRESH = "refresh"


class TokenError(Exception):
    """Fallo de validación de token. El mensaje no distingue causa al cliente."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    *,
    subject: str,
    roles: list[str],
    permissions: list[str],
    expires_minutes: Optional[int] = None,
    extra_claims: Optional[dict[str, Any]] = None,
    secret: Optional[str] = None,
) -> tuple[str, datetime, str]:
    """Emite un access token.

    Devuelve `(token, expira_en, jti)`.

    Claims:
      sub  username o id del actor
      typ  "access" | "refresh" — impide que un refresh se use como access
      jti  id único, para auditoría y revocación
      iat/exp/iss/aud  ventana temporal y de dominio
      roles / perms  resueltos en el login

    `roles` y `perms` viajan DENTRO del token a propósito: así `require_permission`
    no consulta la base en cada request. El precio es que un cambio de rol no
    surte efecto hasta que expire el access (15 min), que es la ventana aceptable y
    por eso el access es corto.

    `secret` permite firmar con `PROVIDER_TOKEN_SECRET` para el super admin, que
    no existe en la tabla `users`.
    """
    key = secret or settings.SECRET_KEY
    minutes = expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_MINUTES
    expires_at = _now() + timedelta(minutes=minutes)
    jti = new_jti()
    now = _now()
    claims: dict[str, Any] = {
        "sub": subject,
        "typ": TOKEN_TYPE_ACCESS,
        "roles": roles,
        "perms": permissions,
        "jti": jti,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    if extra_claims:
        claims.update(extra_claims)
    token = jwt.encode(claims, key, algorithm=settings.ALGORITHM)
    return token, expires_at, jti


def decode_token(
    token: str,
    *,
    expected_type: str = TOKEN_TYPE_ACCESS,
    secret: Optional[str] = None,
    verify_audience: bool = True,
) -> dict[str, Any]:
    """Valida firma, `iss`, `aud` y expiración. Devuelve los claims.

    `iss` y `aud` no son decorativos: sin ellos, un token firmado por otra
    instancia que compartiera la `SECRET_KEY` (un error de configuración, o un
    entorno de pruebas en producción) sería aceptado acá.
    """
    key = secret or settings.SECRET_KEY
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=[settings.ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE if verify_audience else None,
            options={
                "verify_aud": verify_audience,
                "require_exp": True,
                "require_iat": True,
            },
        )
    except JWTError as exc:
        raise TokenError(str(exc)) from exc

    if claims.get("typ") != expected_type:
        raise TokenError(
            f"tipo de token inesperado: {claims.get('typ')!r} != {expected_type!r}"
        )
    return claims


def parse_expiry(token: str) -> datetime:
    """Lee el `exp` de un token sin validar la firma. Solo para uso informativo."""
    claims = jwt.get_unverified_claims(token)
    return datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc)