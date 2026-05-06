"""Centralized application config — all env-driven, no scattered os.environ calls."""
from pydantic_settings import BaseSettings, SettingsConfigDict

# ─────────────────────────────────────────────────────────────────────────────
# CACHE_VERSION — bump this whenever scoring logic, weights, or thresholds
# change in a way that would make old cached verdicts wrong.
#
# Bumping this string makes every existing cached verdict unreachable in one
# step — no manual Redis flush needed. Old keys age out naturally via their TTL.
#
# When to bump:
#   ✓ Changed a score_contribution value in any signal
#   ✓ Changed risk_threshold_caution / risk_threshold_danger
#   ✓ Added or removed a signal
#   ✓ Changed signal logic that affects whether `triggered` fires
#
# When NOT to bump:
#   ✗ Refactored code without changing behavior
#   ✗ Fixed a typo in an explanation string
#   ✗ Renamed a variable
#
# The startup safety check below will warn you if it detects scoring-relevant
# code changed but you forgot to bump this.
# ─────────────────────────────────────────────────────────────────────────────
CACHE_VERSION = "v6"


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

    # ─── Phase 3 ──────────────────────────────────────────────────────────
    # Provider selection — "ollama" (local dev) or "groq" (production).
    # Swap with LLM_PROVIDER env var; no code changes needed.
    llm_provider: str = "ollama"

    # Ollama — local LLM server. host.docker.internal lets the backend
    # container reach Ollama running on the Mac/Windows host.
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: float = 15.0

    # Groq — hosted inference. Free tier covers small-scale testing.
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    # Toggle the LLM signal off entirely (useful when neither provider is
    # available or for debugging). The pipeline just skips it cleanly.
    llm_enabled: bool = True

    # RAG settings
    rag_enabled: bool = True
    rag_corpus_path: str = "app/data/phishing_corpus.jsonl"
    rag_chroma_path: str = "app/data/chroma_db"
    rag_collection_name: str = "phishing_patterns"
    rag_embedding_model: str = "all-MiniLM-L6-v2"
    rag_top_k: int = 5

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
