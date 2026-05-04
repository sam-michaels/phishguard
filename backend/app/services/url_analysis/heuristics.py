"""Fast deterministic URL heuristics.

These run instantly and catch common low-effort phishing patterns. Each
returns a separate SignalResult so the verdict explanation can list every
triggered indicator individually.
"""
import re
from urllib.parse import urlparse

import tldextract

from app.api.schemas.scan import SignalResult

# TLDs heavily abused for free / low-cost phishing domains
SUSPICIOUS_TLDS = {"tk", "ml", "ga", "cf", "gq", "xyz", "top", "loan", "click"}
IP_PATTERN = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


def check_heuristics(url: str) -> list[SignalResult]:
    parsed = urlparse(url)
    extracted = tldextract.extract(url)
    hostname = parsed.hostname or ""
    results: list[SignalResult] = []

    # IP-as-host — legitimate sites always use named domains
    if IP_PATTERN.match(hostname):
        results.append(SignalResult(
            name="ip_host",
            triggered=True,
            score_contribution=30,
            explanation="URL uses raw IP address instead of domain — common phishing pattern.",
        ))

    # @ in URL authority — legacy credential-spoofing trick
    if "@" in parsed.netloc:
        results.append(SignalResult(
            name="at_symbol",
            triggered=True,
            score_contribution=40,
            explanation="URL contains '@' in authority section — known credential-spoofing trick.",
        ))

    # Suspicious TLD
    if extracted.suffix.lower() in SUSPICIOUS_TLDS:
        results.append(SignalResult(
            name="suspicious_tld",
            triggered=True,
            score_contribution=15,
            explanation=f"Domain uses '.{extracted.suffix}' — TLD frequently abused for phishing.",
        ))

    # Punycode / IDN homograph attack indicator
    if "xn--" in hostname:
        results.append(SignalResult(
            name="punycode",
            triggered=True,
            score_contribution=20,
            explanation="Domain uses Punycode encoding — possible homograph attack.",
        ))

    # Excessive subdomains — used to obscure the real registrable domain
    subdomain_parts = extracted.subdomain.split(".") if extracted.subdomain else []
    if len(subdomain_parts) >= 4:
        results.append(SignalResult(
            name="excessive_subdomains",
            triggered=True,
            score_contribution=10,
            explanation=f"URL has {len(subdomain_parts)} subdomain levels — unusually deep.",
        ))

    return results
