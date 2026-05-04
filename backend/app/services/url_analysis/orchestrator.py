"""Run all URL signals in parallel and aggregate them into a verdict."""
import asyncio
from datetime import datetime, timezone

from app.api.schemas.scan import ScanVerdict, SignalResult
from app.core.cache import cache
from app.core.scoring import aggregate_signals
from app.services.url_analysis.domain_age import check_domain_age
from app.services.url_analysis.heuristics import check_heuristics
from app.services.url_analysis.typosquatting import check_typosquatting
from app.services.url_analysis.virustotal import check_virustotal


async def scan_url(url: str) -> ScanVerdict:
    # Cache hit short-circuits everything — keeps repeat scans cheap and fast
    cached_verdict = await cache.get_verdict(url)
    if cached_verdict:
        cached_verdict.cached = True
        return cached_verdict

    # CPU-bound checks → thread pool. Network-bound → direct await.
    # asyncio.gather runs them all concurrently for sub-second total latency.
    typo, heuristic_results, domain_age, vt = await asyncio.gather(
        asyncio.to_thread(check_typosquatting, url),
        asyncio.to_thread(check_heuristics, url),
        check_domain_age(url),
        check_virustotal(url),
    )

    signals: list[SignalResult] = [typo, domain_age, vt] + heuristic_results
    risk_score, verdict, summary = aggregate_signals(signals)

    result = ScanVerdict(
        url=url,
        risk_score=risk_score,
        verdict=verdict,
        signals=signals,
        cached=False,
        scanned_at=datetime.now(timezone.utc),
        summary=summary,
    )

    await cache.set_verdict(url, result)
    return result
