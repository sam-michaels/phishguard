"""Tests for the LLM classifier signal.

Helper functions are tested directly (imported from llm_classifier, which
re-exports them from llm_providers.shared). The full check_llm_classifier
path mocks get_provider() so tests run without any LLM provider available.
Factory tests verify that the correct provider class is instantiated.
"""
from unittest.mock import AsyncMock, patch

import pytest

from app.services.content_analysis.llm_classifier import (
    _build_user_prompt,
    _parse_response,
    _score_from_verdict,
    check_llm_classifier,
)


# ─── Pure-function tests (no mocks needed) ──────────────────────────────────

def test_score_phishing_high_confidence():
    assert _score_from_verdict("phishing", 0.9) == 36


def test_score_phishing_low_confidence():
    assert _score_from_verdict("phishing", 0.4) == 16


def test_score_suspicious_mid_confidence():
    assert _score_from_verdict("suspicious", 0.6) == 12


def test_score_safe_returns_zero():
    assert _score_from_verdict("safe", 0.95) == 0


def test_score_unknown_verdict_returns_zero():
    assert _score_from_verdict("not-a-verdict", 0.99) == 0


def test_parse_clean_json():
    out = _parse_response('{"verdict":"phishing","confidence":0.9,"reasoning":"x"}')
    assert out == {"verdict": "phishing", "confidence": 0.9, "reasoning": "x"}


def test_parse_fenced_json():
    out = _parse_response('```json\n{"verdict":"safe","confidence":0.8,"reasoning":"ok"}\n```')
    assert out is not None
    assert out["verdict"] == "safe"


def test_parse_with_preamble():
    out = _parse_response('Here it is: {"verdict":"suspicious","confidence":0.6,"reasoning":"new"}')
    assert out is not None
    assert out["verdict"] == "suspicious"


def test_parse_garbage_returns_none():
    assert _parse_response("I cannot help with that") is None


def test_build_user_prompt_includes_password_flag():
    prompt = _build_user_prompt("https://x.com", "Login", ["email", "password"])
    assert "Password field present: True" in prompt


def test_build_user_prompt_no_form():
    prompt = _build_user_prompt("https://x.com", None, [])
    assert "(none)" in prompt


# ─── End-to-end (with mocked provider) ──────────────────────────────────────

@pytest.mark.asyncio
async def test_phishing_verdict_triggers_signal():
    mock_provider = AsyncMock()
    mock_provider.classify.return_value = {
        "verdict": "phishing",
        "confidence": 0.9,
        "reasoning": "Typosquat",
    }

    with patch("app.services.content_analysis.llm_classifier.get_provider", return_value=mock_provider):
        result = await check_llm_classifier(
            "https://paypa1.com/login", "PayPal Login", ["password"]
        )

    assert result.triggered is True
    assert result.score_contribution == 36
    assert "phishing" in result.explanation.lower()


@pytest.mark.asyncio
async def test_safe_verdict_does_not_trigger():
    mock_provider = AsyncMock()
    mock_provider.classify.return_value = {
        "verdict": "safe",
        "confidence": 0.95,
        "reasoning": "Established domain",
    }

    with patch("app.services.content_analysis.llm_classifier.get_provider", return_value=mock_provider):
        result = await check_llm_classifier("https://google.com/")

    assert result.triggered is False
    assert result.score_contribution == 0


@pytest.mark.asyncio
async def test_unparseable_response_fails_soft():
    from app.services.content_analysis.llm_providers.base import ProviderResponseError

    mock_provider = AsyncMock()
    mock_provider.classify.side_effect = ProviderResponseError("Unparseable response")

    with patch("app.services.content_analysis.llm_classifier.get_provider", return_value=mock_provider):
        result = await check_llm_classifier("https://example.com/")

    assert result.triggered is False
    assert "not valid JSON" in result.explanation


@pytest.mark.asyncio
async def test_connection_error_fails_soft():
    from app.services.content_analysis.llm_providers.base import ProviderConnectionError

    mock_provider = AsyncMock()
    mock_provider.classify.side_effect = ProviderConnectionError(
        "Ollama unreachable: ConnectError. Is `ollama serve` running?"
    )

    with patch("app.services.content_analysis.llm_classifier.get_provider", return_value=mock_provider):
        result = await check_llm_classifier("https://example.com/")

    assert result.triggered is False
    assert "Ollama unreachable" in result.explanation


# ─── Factory tests ───────────────────────────────────────────────────────────

def test_factory_returns_ollama_by_default():
    from app.services.content_analysis.llm_providers.factory import get_provider
    from app.services.content_analysis.llm_providers.ollama import OllamaProvider

    assert isinstance(get_provider("ollama"), OllamaProvider)


def test_factory_returns_groq():
    from app.services.content_analysis.llm_providers.factory import get_provider
    from app.services.content_analysis.llm_providers.groq import GroqProvider

    assert isinstance(get_provider("groq"), GroqProvider)


def test_factory_unknown_name_falls_back_to_ollama():
    from app.services.content_analysis.llm_providers.factory import get_provider
    from app.services.content_analysis.llm_providers.ollama import OllamaProvider

    assert isinstance(get_provider("nonexistent"), OllamaProvider)
