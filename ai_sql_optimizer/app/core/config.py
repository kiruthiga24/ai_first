from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List

class Settings(BaseSettings):
    # ---------- App Settings ----------
    APP_NAME: str = "SQL Optimizer"
    APP_ENV: str = "production"

    # ---------- CORS ----------
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # ---------- Database ----------
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    DATABASE_URL: str

    # ---------- LLM (Ollama) ----------
    OLLAMA_HOST: str = "http://localhost:11434"
    LLM_MODEL: str = "llama3:8b"

    # ---------- JWT / Security ----------
    JWT_SECRET_KEY: str
    JWT_ALGO: str = "HS256"

    # ---------- GCP / BigQuery ----------
    GCP_PROJECT: str | None = None
    GCP_DATASET: str | None = None
    GCP_CREDENTIALS_PATH: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings():
    return Settings()
