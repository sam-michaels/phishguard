"""End-to-end test URLs for spot-checking the full pipeline.

These tests hit the live backend and require Ollama + Redis + ChromaDB to be
running. They are SKIPPED by default — run them with PHISHGUARD_LIVE=1 set:

    PHISHGUARD_LIVE=1 pytest tests/test_phishing_examples.py -v -s

The URLs below are public examples of phishing patterns. None resolve to live
malicious sites — they're synthetic/hypothetical patterns for testing scoring.
Tweak the assertions as you tune signal weights.
"""
import os

import httpx
import pytest

LIVE = os.getenv("PHISHGUARD_LIVE") == "1"
BACKEND = os.getenv("PHISHGUARD_BACKEND", "http://localhost:8000")

pytestmark = pytest.mark.skipif(not LIVE, reason="Set PHISHGUARD_LIVE=1 to run")


# Each entry: (url, expected_min_score, label)
PHISHING_TEST_URLS = [
    # Lookalike domains — should trigger typosquatting + (likely) LLM
    ("https://paypa1.com/login",       40, "PayPal typosquat"),
    ("https://micros0ft-365-login.com", 30, "Microsoft typosquat with TLD"),

    # IP host — should trigger heuristics + (likely) RAG
    ("http://192.168.1.1/secure-login", 30, "Raw IP login"),

    # Suspicious TLD + brand-impersonating subdomain
    ("https://my-bank.tk/login",       15, "Suspicious TLD"),

    # Subdomain stuffing
    ("https://accounts.google.com.evil-attacker.net/", 20, "Subdomain stuffing"),

    # @ trick
    ("https://attacker.com@evil.example/login", 35, "@-symbol obfuscation"),
]

LEGITIMATE_TEST_URLS = [
    "https://www.google.com/",
    "https://github.com/",
    "https://news.ycombinator.com/",
]


@pytest.mark.parametrize("url,min_score,label", PHISHING_TEST_URLS)
def test_phishing_examples_score_above_threshold(url, min_score, label):
    """Each URL should score at or above the expected threshold."""
    response = httpx.post(
        f"{BACKEND}/api/v1/scan/url",
        json={"url": url},
        timeout=30.0,
    )
    assert response.status_code == 200, f"{label}: backend returned {response.status_code}"

    body = response.json()
    print(f"\n[{label}] {url}")
    print(f"  → score={body['risk_score']} verdict={body['verdict']}")
    print(f"  → summary: {body['summary']}")
    for s in body["signals"]:
        if s["triggered"]:
            print(f"     ✓ {s['name']} (+{s['score_contribution']}): {s['explanation'][:80]}")

    assert body["risk_score"] >= min_score, (
        f"{label}: expected score >= {min_score}, got {body['risk_score']}"
    )


@pytest.mark.parametrize("url", LEGITIMATE_TEST_URLS)
def test_legitimate_sites_remain_safe(url):
    """Known-safe sites should not be flagged."""
    response = httpx.post(
        f"{BACKEND}/api/v1/scan/url",
        json={"url": url},
        timeout=30.0,
    )
    assert response.status_code == 200

    body = response.json()
    print(f"\n[legitimate] {url} → score={body['risk_score']} verdict={body['verdict']}")
    assert body["verdict"] == "safe", f"{url} flagged as {body['verdict']}: {body['summary']}"
