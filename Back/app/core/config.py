from typing import ClassVar, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/territorial_mvp"
    SECRET_KEY: str = "supersecretkey-dev-only"
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: ClassVar[List[str]] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]

    model_config = {"case_sensitive": True}


settings = Settings()