"""Run all URL signals in parallel and aggregate them into a verdict."""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from app.api.schemas.scan import ScanVerdict, SignalResult
from app.core.cache import cache
from app.core.scoring import aggregate_signals
from app.services.content_analysis.llm_classifier import check_llm_classifier
from app.services.threat_intel.rag_retriever import check_rag_threat_intel
from app.services.url_analysis.domain_age import check_domain_age
from app.services.url_analysis.heuristics import check_heuristics
from app.services.url_analysis.typosquatting import check_typosquatting
from app.services.url_analysis.virustotal import check_virustotal


async def scan_url(
    url: str,
    page_title: Optional[str] = None,
    form_fields: Optional[list[str]] = None,
) -> ScanVerdict:
    # Cache hit short-circuits everything — keeps repeat scans cheap and fast
    cached_verdict = await cache.get_verdict(url)
    if cached_verdict:
        cached_verdict.cached = True
        return cached_verdict

    # All six signals run concurrently. Total latency = slowest single signal.
    # LLM is typically slowest (1-2s on local Ollama); RAG retrieval is fast
    # (~50ms after warmup); deterministic signals are <500ms each. The cache
    # makes the slow path a one-time cost per URL.
    typo, heuristic_results, domain_age, vt, llm, rag = await asyncio.gather(
        asyncio.to_thread(check_typosquatting, url),
        asyncio.to_thread(check_heuristics, url),
        check_domain_age(url),
        check_virustotal(url),
        check_llm_classifier(url, page_title, form_fields),
        check_rag_threat_intel(url, page_title, form_fields),
    )

    signals: list[SignalResult] = [typo, domain_age, vt, llm, rag] + heuristic_results
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

    # Only cache when all signals ran cleanly. A degraded result (provider
    # unreachable, embedding model not loaded, etc.) shouldn't be locked in
    # for hours — the next scan should retry with a fresh pipeline.
    if not any(s.degraded for s in signals):
        await cache.set_verdict(url, result)
    return result
