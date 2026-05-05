"""Centralized application config — all env-driven, no scattered os.environ calls."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # External API keys
    virustotal_api_key: str = ""

    # Infrastructure
    redis_url: str = "redis://localhost:6379"

    # CORS — regex-matched so dynamic extension IDs are accepted without
    # needing to know them ahead of time. Firefox uses moz-extension://<UUID>
    # which can contain uppercase hex; Chrome uses chrome-extension://<32 lowercase letters>.
    cors_origin_regex: str = (
        r"^(chrome-extension://[a-z]{32}|"
        r"moz-extension://[a-fA-F0-9-]+|"
        r"http://localhost(:\d+)?|"
        r"http://127\.0\.0\.1(:\d+)?)$"
    )

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
