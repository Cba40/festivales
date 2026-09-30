import json
import os
from pathlib import Path
from typing import List, Optional

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
    SECRET_KEY: str = "supersecretkey-dev-only"
    ALGORITHM: str = "HS256"

    model_config = {"case_sensitive": True}


settings = Settings()
