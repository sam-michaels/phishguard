"""Abstract base for LLM providers."""
from abc import ABC, abstractmethod
from typing import Optional


class ProviderConnectionError(Exception):
    """Provider endpoint unreachable, timed out, or rejected credentials."""


class ProviderResponseError(Exception):
    """Provider returned a response that couldn't be parsed into the expected schema."""


class LLMProvider(ABC):
    @abstractmethod
    async def classify(
        self,
        url: str,
        page_title: Optional[str],
        form_fields: list[str],
    ) -> dict:
        """Classify a URL for phishing risk.

        Returns a dict with keys: verdict, confidence, reasoning.
        Raises ProviderConnectionError or ProviderResponseError on failure.
        All other exceptions propagate to the caller for fail-soft handling.
        """

    async def is_reachable(self) -> bool:
        """Quick liveness check used by the health endpoint.

        Default: True. Providers override this with a real probe.
        """
        return True
