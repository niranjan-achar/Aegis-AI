"""Application settings and shared path helpers for Aegis-AI."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Environment-driven settings loaded from backend/.env."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="Aegis-AI API", alias="AEGIS_APP_NAME")
    env: str = Field(default="development", alias="AEGIS_ENV")
    host: str = Field(default="0.0.0.0", alias="AEGIS_HOST")
    port: int = Field(default=8000, alias="AEGIS_PORT")
    cors_origins: str = Field(default="http://localhost:5173", alias="AEGIS_CORS_ORIGINS")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="AEGIS_REDIS_URL")
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0", alias="AEGIS_CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1", alias="AEGIS_CELERY_RESULT_BACKEND"
    )
    cache_ttl_seconds: int = Field(default=604800, alias="AEGIS_CACHE_TTL_SECONDS")
    upload_dir: Path = Field(default=BACKEND_DIR / "tmp" / "uploads", alias="AEGIS_UPLOAD_DIR")
    image_dir: Path = Field(default=BACKEND_DIR / "tmp" / "images", alias="AEGIS_IMAGE_DIR")
    xai_dir: Path = Field(default=BACKEND_DIR / "tmp" / "xai", alias="AEGIS_XAI_DIR")
    model_dir: Path = Field(default=BACKEND_DIR / "models", alias="AEGIS_MODEL_DIR")
    rules_dir: Path = Field(default=BACKEND_DIR / "rules", alias="AEGIS_RULES_DIR")
    data_dir: Path = Field(default=BACKEND_DIR / "data", alias="AEGIS_DATA_DIR")
    mlflow_tracking_uri: str = Field(
        default="file:./backend/mlruns", alias="AEGIS_MLFLOW_TRACKING_URI"
    )
    mongo_uri: str = Field(default="", alias="AEGIS_MONGO_URI")
    mongo_db: str = Field(default="aegis_ai", alias="AEGIS_MONGO_DB")
    telemetry_store_path: Path = Field(
        default=BACKEND_DIR / "data" / "dashboard_store.json",
        alias="AEGIS_TELEMETRY_STORE_PATH",
    )
    network_poll_seconds: int = Field(default=6, alias="AEGIS_NETWORK_POLL_SECONDS")
    watch_extensions: str = Field(
        default=".exe,.dll,.scr,.bat,.ps1,.cmd,.com,.zip,.rar",
        alias="AEGIS_WATCH_EXTENSIONS",
    )

    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def watch_extension_list(self) -> list[str]:
        return [item.strip().lower() for item in self.watch_extensions.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""

    settings = Settings()
    for directory in (settings.upload_dir, settings.image_dir, settings.xai_dir):
        directory.mkdir(parents=True, exist_ok=True)
    settings.model_dir.mkdir(parents=True, exist_ok=True)
    settings.rules_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings
