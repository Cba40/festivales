import json
import os
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

# `Settings` no declara `env_file`, asi que pydantic-settings NUNCA leyo el
# `.env` del repo: todos los valores venían de los defaults de la clase o de
# variables de entorno reales. Eso dejaba `Back/.env` como decorativo, y hacia
# que `TEST_DATABASE_URL` fuera invisible para los tests. Se carga el archivo a
# mano antes de construir `Settings`, sin pisar variables ya definidas en el
# entorno (que tienen precedencia).
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
if _ENV_PATH.is_file():
    for _line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _, _value = _line.partition("=")
        os.environ.setdefault(_key.strip(), _value.strip())


def parse_cors_origins(raw: Optional[str]) -> List[str]:
    if not raw:
        return ["*"]
    stripped = raw.strip()
    if not stripped:
        return ["*"]
    if stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                cleaned = [str(item).strip() for item in parsed if item is not None and str(item).strip()]
                return cleaned if cleaned else ["*"]
        except (json.JSONDecodeError, TypeError):
            pass
        return [stripped]
    if "," in stripped:
        return [origin.strip() for origin in stripped.split(",") if origin.strip()]
    return [stripped]


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/territorial_mvp"
    # Base que usa la suite de tests. Distinta de DATABASE_URL a proposito: el
    # fixture `test_engine` de tests/conftest.py borra el schema `public` de esta
    # base en cada corrida. El nombre debe terminar en `_test`; conftest.py
    # aborta la suite si no se cumple.
    TEST_DATABASE_URL: Optional[str] = None

    # ── Clave de firma ──────────────────────────────────────────────────────
    #
    # SIN DEFAULT, a proposito. Antes valía `"supersecretkey-dev-only"`, que
    # estaba en el codigo: cualquier despliegue que olvidara el `.env` firmaba
    # sus tokens con una clave publica del repositorio, y como el algoritmo es
    # HS256 (simetrico) la misma clave firma y verifica. Un atacante que leyera
    # el repo podia fabricar tokens de administrador para cualquier instancia.
    #
    # Ahora no hay valor por defecto: si falta, la app no arranca. Ver
    # `_validar_secret_key` mas abajo, que ademas exige 32 caracteres.
    SECRET_KEY: str = Field(..., min_length=32)

    ALGORITHM: str = "HS256"

    # Emisor y audiencia del JWT. Se validan en `decode` además de la firma, así
    # que un token de otra instancia del mismo proveedor (misma SECRET_KEY si el
    # operador la compartiera por error) no sirve acá.
    JWT_ISSUER: str = "festivales"
    JWT_AUDIENCE: str = "festivales-api"

    # ── Vigencia de tokens ──────────────────────────────────────────────────
    #
    # Access corto a propósito: el refresh es lo que sostiene la sesión, así que
    # un access robado sirve 15 minutos como máximo y el logout revoca el
    # refresh, que es el de larga vida.
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 7

    # ── Bootstrap del proveedor (nosotros) ──────────────────────────────────
    #
    # El super admin NO es una fila en la tabla `users` del cliente. Si lo fuera,
    # un administrador municipal con permiso de `users:manage` podría otorgarse
    # SUPER_ADMIN leyendo la tabla. En su lugar, estos usernames se resuelven
    # contra el proveedor y emiten un token firmado con una clave DISTINTA
    # (`PROVIDER_TOKEN_SECRET`), de modo que la cuenta no existe en el lado del
    # cliente: no se puede ver, ni listar, ni revocar, ni duplicar.
    #
    # Viven en el vault del entorno, nunca en el `.env` del repo ni en la BD.
    SUPER_ADMIN_USERNAMES: List[str] = Field(default_factory=list)
    # Si se deja vacía, un super admin solo puede entrar por el flujo normal de
    # la tabla `users`. Se separa para poder deployments sin acceso de soporte.
    PROVIDER_TOKEN_SECRET: Optional[str] = None

    # Lockout por intentos fallidos en el login.
    LOGIN_MAX_FAILED_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Rate limiting de las rutas públicas.
    #
    # `REDIS_URL` estaba declarada en `.env` pero ningún módulo la leía: era una
    # variable muerta, y sin cliente `redis` instalado el conteo distribuido no
    # era posible. Ahora la lee `src/infrastructure/middleware/rate_limit.py`.
    # Sin valor (o si el ping falla) el rate limit degrada a un contador en
    # memoria del proceso, que en Vercel serverless es por instancia.
    REDIS_URL: Optional[str] = None
    # Interruptor de emergencia: en `False` las rutas públicas no cuentan nada.
    RATE_LIMIT_ENABLED: bool = True

    model_config = {"case_sensitive": True}

    @field_validator("SUPER_ADMIN_USERNAMES", mode="before")
    @classmethod
    def _parse_usernames(cls, v):
        """Acepta `"a@x.com,b@y.com"` además de una lista real.

        Las variables de entorno siempre llegan como string; sin esto, un
        `SUPER_ADMIN_USERNAMES=a@x.com,b@y.com` en el vault fallaría el arranque
        de la app.
        """
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def _validar_secret_key(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY debe tener al menos 32 caracteres. "
                f"Recibidos {len(v)}. Generá una con: "
                "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        if v.startswith("supersecret") or v.lower() in {"changeme", "secret"}:
            raise ValueError(
                "SECRET_KEY parece un valor de ejemplo conocido. No es una clave real."
            )
        return v

    @model_validator(mode="after")
    def _validar_bootstrap_proveedor(self) -> "Settings":
        """Falla al arrancar si el bootstrap del proveedor quedó a medias.

        Declarar `SUPER_ADMIN_USERNAMES` sin `PROVIDER_TOKEN_SECRET` es el peor
        de los dos casos: el username existiría pero el token saldría firmado con
        la `SECRET_KEY` de los usuarios, o sea indistinguible de un super admin
        de la BD. Se prefiere el arranque ruidoso.
        """
        if self.SUPER_ADMIN_USERNAMES and not self.PROVIDER_TOKEN_SECRET:
            raise ValueError(
                "SUPER_ADMIN_USERNAMES está configurado pero PROVIDER_TOKEN_SECRET "
                "no. Defínelo, o quitá los usernames. No se puede emitir el token "
                "del proveedor con la clave de los usuarios."
            )
        if self.PROVIDER_TOKEN_SECRET and len(self.PROVIDER_TOKEN_SECRET) < 32:
            raise ValueError(
                "PROVIDER_TOKEN_SECRET debe tener al menos 32 caracteres. "
                f"Recibidos {len(self.PROVIDER_TOKEN_SECRET)}."
            )
        if self.PROVIDER_TOKEN_SECRET == self.SECRET_KEY:
            raise ValueError(
                "PROVIDER_TOKEN_SECRET no puede ser igual a SECRET_KEY: son "
                "claves de dominios distintos y compartirla habilita emisión de "
                "tokens de proveedor desde el lado de los usuarios."
            )
        return self


settings = Settings()
