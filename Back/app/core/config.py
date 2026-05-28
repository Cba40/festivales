# backend/app/core/config.py

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/territorial_mvp"
    SECRET_KEY: str = "supersecretkey-dev-only"
    ALGORITHM: str = "HS256"

    model_config = {"case_sensitive": True}


settings = Settings()
