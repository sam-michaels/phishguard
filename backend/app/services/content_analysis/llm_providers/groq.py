"""Groq provider — calls the Groq hosted API via the groq Python SDK."""
import logging
from typing import Optional

from app.config import settings

from .base import LLMProvider, ProviderConnectionError, ProviderResponseError
from .shared import SYSTEM_PROMPT, _build_user_prompt, _parse_response

logger = logging.getLogger("phishguard")


class GroqProvider(LLMProvider):
    async def classify(
        self,
        url: str,
        page_title: Optional[str],
        form_fields: list[str],
    ) -> dict:
        import groq  # deferred so missing package only errors when Groq is actually used

        client = groq.AsyncGroq(api_key=settings.groq_api_key)
        user_message = _build_user_prompt(url, page_title, form_fields)

        try:
            completion = await client.chat.completions.create(
                model=settings.groq_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )
        except groq.APIConnectionError as e:
            raise ProviderConnectionError(f"Groq API unreachable: {type(e).__name__}") from e
        except groq.AuthenticationError as e:
            raise ProviderConnectionError("Groq authentication failed — check GROQ_API_KEY") from e
        except groq.RateLimitError as e:
            raise ProviderConnectionError("Groq rate limit exceeded") from e
        except groq.APIError as e:
            raise ProviderConnectionError(f"Groq API error: {type(e).__name__}") from e

        raw = completion.choices[0].message.content or ""
        parsed = _parse_response(raw)
        if parsed is None:
            logger.warning(f"Groq returned unparseable response: {raw[:200]!r}")
            raise ProviderResponseError(f"Unparseable Groq response: {raw[:200]!r}")
        return parsed

    async def is_reachable(self) -> bool:
        # Groq has no free ping endpoint; API key presence is the best proxy.
        return bool(settings.groq_api_key)
