import json
from typing import List, Optional

from pydantic_settings import BaseSettings


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
    SECRET_KEY: str = "supersecretkey-dev-only"
    ALGORITHM: str = "HS256"

    model_config = {"case_sensitive": True}


settings = Settings()
