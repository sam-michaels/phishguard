"""Centralized application config — all env-driven, no scattered os.environ calls."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # External API keys
    virustotal_api_key: str = ""

    # Infrastructure
    redis_url: str = "redis://localhost:6379"

    # CORS — extension origins go here once we have an extension ID
    cors_origins: list[str] = [
        "chrome-extension://*",
        "http://localhost:3000",
    ]

    # Operational
    environment: str = "development"
    log_level: str = "INFO"

    # Cache TTLs (seconds)
    cache_ttl_safe: int = 3600
    cache_ttl_caution: int = 7200
    cache_ttl_danger: int = 86400

    # Scoring thresholds (risk_score 0-100)
    risk_threshold_caution: int = 31
    risk_threshold_danger: int = 66

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
