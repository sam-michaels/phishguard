"""Ollama provider — calls the local Ollama HTTP API via httpx."""
import logging
from typing import Optional

import httpx

from app.config import settings

from .base import LLMProvider, ProviderConnectionError, ProviderResponseError
from .shared import SYSTEM_PROMPT, _build_user_prompt, _parse_response

logger = logging.getLogger("phishguard")


class OllamaProvider(LLMProvider):
    async def classify(
        self,
        url: str,
        page_title: Optional[str],
        form_fields: list[str],
    ) -> dict:
        user_message = _build_user_prompt(url, page_title, form_fields)
        try:
            async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/chat",
                    json={
                        "model": settings.ollama_model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_message},
                        ],
                        "stream": False,
                        "format": "json",  # Ollama-native structured output
                        "options": {"temperature": 0.1},
                    },
                )
        except httpx.RequestError as e:
            raise ProviderConnectionError(
                f"Ollama unreachable: {type(e).__name__}. Is `ollama serve` running?"
            ) from e

        if response.status_code != 200:
            raise ProviderConnectionError(
                f"Ollama returned HTTP {response.status_code} — signal skipped."
            )

        body = response.json()
        raw = body.get("message", {}).get("content", "")
        parsed = _parse_response(raw)
        if parsed is None:
            logger.warning(f"Ollama returned unparseable response: {raw[:200]!r}")
            raise ProviderResponseError(f"Unparseable Ollama response: {raw[:200]!r}")
        return parsed

    async def is_reachable(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{settings.ollama_base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False
