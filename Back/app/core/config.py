import json
from typing import Any, List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/territorial_mvp"
    SECRET_KEY: str = "supersecretkey-dev-only"
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: Any = "*"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        if v is None:
            return ["*"]
        if isinstance(v, list):
            cleaned = [str(item).strip() for item in v if item is not None and str(item).strip()]
            return cleaned if cleaned else ["*"]
        if isinstance(v, str):
            stripped = v.strip()
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
        return ["*"]

    model_config = {"case_sensitive": True}


settings = Settings()
