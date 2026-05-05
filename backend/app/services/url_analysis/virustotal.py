"""VirusTotal v3 URL reputation check.

Free tier: 4 requests/minute, 500/day. Sufficient for early dev — Redis cache
keeps repeated hits free. For production scale, upgrade or add rate limiting.
"""
import base64

import httpx

from app.api.schemas.scan import SignalResult
from app.config import settings

VT_API_BASE = "https://www.virustotal.com/api/v3"


async def check_virustotal(url: str) -> SignalResult:
    if not settings.virustotal_api_key:
        return SignalResult(
            name="virustotal",
            triggered=False,
            explanation="VirusTotal API key not configured — skipped.",
        )

    # VT v3 expects base64url-encoded URL (no padding) as the resource ID
    url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{VT_API_BASE}/urls/{url_id}",
                headers={"x-apikey": settings.virustotal_api_key},
            )

        if response.status_code == 404:
            # URL never analyzed by VT before — skip rather than false-clean
            return SignalResult(
                name="virustotal",
                triggered=False,
                explanation="URL not previously analyzed by VirusTotal.",
            )

        if response.status_code != 200:
            return SignalResult(
                name="virustotal",
                triggered=False,
                explanation=f"VirusTotal API error: {response.status_code}",
            )

        data = response.json()
        stats = data["data"]["attributes"]["last_analysis_stats"]
        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)

        # Tiered scoring by vendor consensus.
        #
        # VirusTotal aggregates ~90 vendors of varying quality. A single
        # vendor flagging a major site is almost always noise (e.g. a category
        # filter mislabeling youtube.com as "media streaming = malicious").
        # Real signal comes from MULTIPLE vendors agreeing.
        if malicious >= 5:
            return SignalResult(
                name="virustotal",
                triggered=True,
                score_contribution=55,
                explanation=f"Strong consensus: flagged as malicious by {malicious} vendors.",
                metadata=stats,
            )
        if malicious >= 2:
            return SignalResult(
                name="virustotal",
                triggered=True,
                score_contribution=30,
                explanation=f"Moderate consensus: {malicious} vendors flagged as malicious.",
                metadata=stats,
            )
        if malicious >= 1 or suspicious >= 3:
            # Show the signal so the user can see the data, but contribute
            # only a small amount — not enough to flip a verdict on its own
            return SignalResult(
                name="virustotal",
                triggered=True,
                score_contribution=5,
                explanation=(
                    f"Weak signal: {malicious} malicious / {suspicious} suspicious "
                    f"verdicts out of {sum(stats.values())} vendors. "
                    f"Likely noise from a single vendor unless other signals also trigger."
                ),
                metadata=stats,
            )

        return SignalResult(
            name="virustotal",
            triggered=False,
            explanation=f"Clean across {sum(stats.values())} vendor checks.",
            metadata=stats,
        )
    except httpx.RequestError as e:
        return SignalResult(
            name="virustotal",
            triggered=False,
            explanation=f"VirusTotal request failed: {type(e).__name__}",
        )