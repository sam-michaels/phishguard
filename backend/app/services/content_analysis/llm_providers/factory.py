"""Factory that returns the configured LLM provider."""
from typing import Optional

from app.config import settings

from .base import LLMProvider


def get_provider(name: Optional[str] = None) -> LLMProvider:
    """Return a provider instance for the given name (or settings.llm_provider).

    Imports are deferred so unused providers don't pull in their dependencies
    at startup (groq SDK is only imported when name == "groq").
    """
    resolved = name or settings.llm_provider
    if resolved == "groq":
        from .groq import GroqProvider
        return GroqProvider()
    from .ollama import OllamaProvider
    return OllamaProvider()
