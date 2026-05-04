"""Aggregate per-signal contributions into a final verdict."""
from app.api.schemas.scan import SignalResult
from app.config import settings


def aggregate_signals(signals: list[SignalResult]) -> tuple[int, str, str]:
    """Returns (risk_score, verdict_label, human_summary)."""
    triggered = [s for s in signals if s.triggered]
    raw_score = sum(s.score_contribution for s in triggered)
    risk_score = min(raw_score, 100)

    if risk_score >= settings.risk_threshold_danger:
        verdict = "danger"
    elif risk_score >= settings.risk_threshold_caution:
        verdict = "caution"
    else:
        verdict = "safe"

    if not triggered:
        summary = "No threat indicators detected."
    elif len(triggered) == 1:
        summary = triggered[0].explanation
    else:
        top = sorted(triggered, key=lambda s: -s.score_contribution)[:2]
        summary = (
            f"{len(triggered)} indicators triggered. "
            f"Top concerns: {top[0].name}, {top[1].name}."
        )

    return risk_score, verdict, summary
