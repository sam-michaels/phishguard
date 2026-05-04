"""Risk-score aggregator tests."""
from app.api.schemas.scan import SignalResult
from app.core.scoring import aggregate_signals


def _signal(name: str, score: int, triggered: bool = True) -> SignalResult:
    return SignalResult(
        name=name,
        triggered=triggered,
        score_contribution=score,
        explanation=f"test signal {name}",
    )


def test_no_signals_returns_safe():
    score, verdict, _ = aggregate_signals([])
    assert score == 0
    assert verdict == "safe"


def test_only_untriggered_signals_returns_safe():
    score, verdict, _ = aggregate_signals([_signal("a", 80, triggered=False)])
    assert score == 0
    assert verdict == "safe"


def test_caution_threshold():
    score, verdict, _ = aggregate_signals([_signal("a", 35)])
    assert verdict == "caution"


def test_danger_threshold():
    score, verdict, _ = aggregate_signals([_signal("a", 45), _signal("b", 30)])
    assert verdict == "danger"


def test_score_capped_at_100():
    score, _, _ = aggregate_signals([_signal("a", 80), _signal("b", 80)])
    assert score == 100


def test_summary_lists_top_signals():
    signals = [
        _signal("typosquatting", 45),
        _signal("ip_host", 30),
        _signal("at_symbol", 40),
    ]
    _, _, summary = aggregate_signals(signals)
    assert "3 indicators" in summary
