"""Domain age check via WHOIS — newly-registered domains are a phishing red flag."""
import asyncio
from datetime import datetime, timezone

import tldextract
import whois

from app.api.schemas.scan import SignalResult


def _whois_lookup_sync(domain: str):
    return whois.whois(domain)


async def check_domain_age(url: str) -> SignalResult:
    extracted = tldextract.extract(url)

    if not extracted.domain or not extracted.suffix:
        return SignalResult(
            name="domain_age",
            triggered=False,
            explanation="Domain unparseable.",
        )

    domain = f"{extracted.domain}.{extracted.suffix}"

    try:
        # python-whois is sync — push to thread pool so we don't block the event loop
        w = await asyncio.to_thread(_whois_lookup_sync, domain)
        creation_date = w.creation_date
        if isinstance(creation_date, list):
            creation_date = creation_date[0] if creation_date else None

        if not creation_date:
            return SignalResult(
                name="domain_age",
                triggered=False,
                explanation="WHOIS creation date unavailable.",
            )

        if creation_date.tzinfo is None:
            creation_date = creation_date.replace(tzinfo=timezone.utc)

        age_days = (datetime.now(timezone.utc) - creation_date).days

        if age_days < 7:
            return SignalResult(
                name="domain_age",
                triggered=True,
                score_contribution=35,
                explanation=f"Domain registered only {age_days} days ago — high phishing risk.",
                metadata={"age_days": age_days},
            )
        if age_days < 30:
            return SignalResult(
                name="domain_age",
                triggered=True,
                score_contribution=20,
                explanation=f"Domain registered {age_days} days ago — newer domains warrant caution.",
                metadata={"age_days": age_days},
            )
        if age_days < 90:
            return SignalResult(
                name="domain_age",
                triggered=True,
                score_contribution=10,
                explanation=f"Domain registered {age_days} days ago — moderately new.",
                metadata={"age_days": age_days},
            )
        return SignalResult(
            name="domain_age",
            triggered=False,
            explanation=f"Domain registered {age_days} days ago — established.",
            metadata={"age_days": age_days},
        )
    except Exception as e:  # WHOIS lookups fail for many reasons — never let them crash the scan
        return SignalResult(
            name="domain_age",
            triggered=False,
            explanation=f"WHOIS lookup failed: {type(e).__name__}",
        )
