"""LLM-based phishing classifier — delegates to the configured provider.

The provider (Ollama or Groq) is selected via settings.llm_provider and
swapped with no code changes — only an env variable. Fails soft: if the
provider is unreachable or returns garbage, the signal returns triggered=False
and the rest of the pipeline continues unaffected.
"""
import logging
from typing import Optional

from app.api.schemas.scan import SignalResult
from app.config import settings
from app.services.content_analysis.llm_providers.base import (
    ProviderConnectionError,
    ProviderResponseError,
)
from app.services.content_analysis.llm_providers.factory import get_provider

# Re-exported so existing test imports (from llm_classifier import _build_user_prompt ...)
# continue to work without changes.
from app.services.content_analysis.llm_providers.shared import (  # noqa: F401
    _build_user_prompt,
    _parse_response,
)

logger = logging.getLogger("phishguard")


def _score_from_verdict(verdict: str, confidence: float) -> int:
    """Map LLM verdict + confidence to a score contribution.

    Bounded so a single hallucinated 'phishing' verdict on a benign site
    can be overridden by other signals voting safe. The LLM is one signal
    among many, not the final word.
    """
    if verdict == "phishing":
        return int(40 * confidence)  # max 40
    if verdict == "suspicious":
        return int(20 * confidence)  # max 20
    return 0


async def check_llm_classifier(
    url: str,
    page_title: Optional[str] = None,
    form_fields: Optional[list[str]] = None,
) -> SignalResult:
    if not settings.llm_enabled:
        return SignalResult(
            name="llm_classifier",
            triggered=False,
            explanation="LLM signal disabled in config.",
        )

    try:
        provider = get_provider()
        parsed = await provider.classify(url, page_title, form_fields or [])
    except ProviderConnectionError as e:
        return SignalResult(
            name="llm_classifier",
            triggered=False,
            explanation=str(e),
        )
    except ProviderResponseError:
        return SignalResult(
            name="llm_classifier",
            triggered=False,
            explanation="LLM response was not valid JSON — signal skipped.",
        )
    except Exception as e:
        logger.exception("LLM classifier crashed")
        return SignalResult(
            name="llm_classifier",
            triggered=False,
            explanation=f"LLM classifier error: {type(e).__name__}",
        )

    verdict = str(parsed.get("verdict", "safe")).lower()
    confidence = float(parsed.get("confidence", 0.5))
    reasoning = str(parsed.get("reasoning", "(no reasoning provided)"))[:200]
    score = _score_from_verdict(verdict, confidence)

    if score == 0:
        return SignalResult(
            name="llm_classifier",
            triggered=False,
            explanation=f"LLM verdict: safe ({confidence:.0%} confidence). {reasoning}",
            metadata={"verdict": verdict, "confidence": confidence},
        )

    return SignalResult(
        name="llm_classifier",
        triggered=True,
        score_contribution=score,
        explanation=f"LLM verdict: {verdict} ({confidence:.0%} confidence). {reasoning}",
        metadata={"verdict": verdict, "confidence": confidence},
    )
