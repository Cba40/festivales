from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/territorial_mvp"
    SECRET_KEY: str = "supersecretkey-dev-only"
    ALGORITHM: str = "HS256"
    CORS_ORIGINS: List[str] = ["*"]

    model_config = {"case_sensitive": True}


settings = Settings()