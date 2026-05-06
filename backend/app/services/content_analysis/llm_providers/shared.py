"""Shared prompt templates and response parsing — provider-agnostic."""
import json
from typing import Optional

# Prompt is intentionally specific about output format. Llama 3.1 8B is small
# enough that less-explicit prompts produce inconsistent JSON. The "Output
# ONLY a JSON object" framing reliably gets us parseable output.
SYSTEM_PROMPT = """You are a security analyst classifying web pages for phishing risk.

Analyze the page metadata and return a single JSON object with exactly these fields:
{
  "verdict": "safe" | "suspicious" | "phishing",
  "confidence": 0.0 to 1.0,
  "reasoning": "one short sentence explaining your judgment"
}

Consider these phishing indicators:
- Domain mismatches (URL claims to be one brand, content suggests another)
- Credential collection forms on suspicious or unbranded domains
- Urgency language in titles ("verify now", "account suspended")
- Lookalike domains (paypa1, g00gle, micros0ft-secure)
- Generic login pages on domains that shouldn't have them
- Mismatch between domain and apparent service

Output ONLY the JSON object. No prose, no code fences, no preamble."""


def _build_user_prompt(url: str, page_title: Optional[str], form_fields: list[str]) -> str:
    """Compose the user message with the data we want classified."""
    has_password = any("password" in f.lower() for f in form_fields)
    has_payment = any(("ac:cc-" in f.lower()) or ("credit" in f.lower()) for f in form_fields)

    parts = [
        f"URL: {url}",
        f"Page title: {page_title or '(none)'}",
        f"Form fields detected: {', '.join(form_fields) if form_fields else '(none)'}",
        f"Password field present: {has_password}",
        f"Payment field present: {has_payment}",
    ]
    return "\n".join(parts)


def _parse_response(raw: str) -> Optional[dict]:
    """Best-effort extraction of the JSON object from the model's reply.

    Models sometimes wrap JSON in code fences or add a sentence of preamble.
    We strip those defensively rather than fail the whole signal.
    """
    text = raw.strip()
    # Strip fenced code blocks
    if text.startswith("```"):
        text = text.split("```", 2)[-2] if text.count("```") >= 2 else text
        text = text.replace("json", "", 1).strip()
    # Find first { and last } — handles preambles like "Here is the JSON: {...}"
    first, last = text.find("{"), text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        return None
    try:
        return json.loads(text[first : last + 1])
    except json.JSONDecodeError:
        return None
