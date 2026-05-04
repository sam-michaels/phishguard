"""Typosquatting detection via Levenshtein distance to popular domains.

A registered domain (e.g. paypa1.com) within 1-2 edits of a high-value target
(paypal.com) is one of the strongest single phishing signals available.
"""
import Levenshtein
import tldextract

from app.api.schemas.scan import SignalResult
from app.data.popular_domains import POPULAR_DOMAINS


def check_typosquatting(url: str) -> SignalResult:
    extracted = tldextract.extract(url)

    if not extracted.domain or not extracted.suffix:
        return SignalResult(
            name="typosquatting",
            triggered=False,
            explanation="Could not parse domain.",
        )

    registered = f"{extracted.domain}.{extracted.suffix}".lower()

    # The domain IS the popular target — not squatting it
    if registered in POPULAR_DOMAINS:
        return SignalResult(
            name="typosquatting",
            triggered=False,
            explanation=f"'{registered}' is a known legitimate domain.",
        )

    closest_match: str | None = None
    min_distance = float("inf")

    for target in POPULAR_DOMAINS:
        dist = Levenshtein.distance(registered, target)
        if dist < min_distance:
            min_distance = dist
            closest_match = target

    if min_distance == 1:
        return SignalResult(
            name="typosquatting",
            triggered=True,
            score_contribution=45,
            explanation=(
                f"Domain '{registered}' is 1 edit away from '{closest_match}'. "
                "Strong typosquatting signal."
            ),
            metadata={"closest_match": closest_match, "distance": min_distance},
        )
    if min_distance == 2:
        return SignalResult(
            name="typosquatting",
            triggered=True,
            score_contribution=25,
            explanation=(
                f"Domain '{registered}' is 2 edits away from '{closest_match}'. "
                "Possible typosquatting."
            ),
            metadata={"closest_match": closest_match, "distance": min_distance},
        )

    return SignalResult(
        name="typosquatting",
        triggered=False,
        explanation=(
            f"No close match to popular targets "
            f"(closest: '{closest_match}', distance {min_distance})."
        ),
    )
