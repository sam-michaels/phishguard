"""Cache version safety check.

Run at startup. Hashes the contents of scoring-relevant files and compares
against a stored fingerprint. If they differ AND CACHE_VERSION wasn't bumped,
emits a loud warning so you don't accidentally ship buggy scoring to users.

This is a *warning*, not an error — sometimes you genuinely want to refactor
scoring code without bumping the version (e.g. extracting a helper function
without changing behavior). The warning gives you a moment to decide.
"""
import hashlib
import logging
from pathlib import Path

from app.config import CACHE_VERSION

logger = logging.getLogger("phishguard")

# Files whose changes should trigger a CACHE_VERSION bump
SCORING_FILES = [
    "app/services/url_analysis/typosquatting.py",
    "app/services/url_analysis/domain_age.py",
    "app/services/url_analysis/virustotal.py",
    "app/services/url_analysis/heuristics.py",
    "app/core/scoring.py",
]

FINGERPRINT_FILE = Path("/tmp/phishguard_scoring_fingerprint")


def _compute_fingerprint() -> str:
    """SHA256 over the concatenated contents of all scoring files."""
    h = hashlib.sha256()
    base = Path(__file__).parent.parent.parent  # backend/
    for relpath in SCORING_FILES:
        path = base / relpath
        if path.exists():
            h.update(path.read_bytes())
    return h.hexdigest()[:16]  # short prefix is enough


def check_scoring_fingerprint() -> None:
    current = _compute_fingerprint()
    record = f"{CACHE_VERSION}:{current}"

    if not FINGERPRINT_FILE.exists():
        FINGERPRINT_FILE.write_text(record)
        logger.info(f"Scoring fingerprint initialized: {record}")
        return

    previous = FINGERPRINT_FILE.read_text().strip()
    prev_version, _, prev_hash = previous.partition(":")

    if previous == record:
        return  # all good — nothing changed

    if prev_version == CACHE_VERSION and prev_hash != current:
        # Code changed but version didn't — likely a bug
        logger.warning(
            "⚠ SCORING CODE CHANGED but CACHE_VERSION (%s) was NOT bumped.\n"
            "   If this change affects scores, bump CACHE_VERSION in app/config.py\n"
            "   so old cached verdicts become unreachable.\n"
            "   If this change is purely cosmetic (refactor, typo fix, comment),\n"
            "   you can safely ignore this warning.",
            CACHE_VERSION,
        )
    elif prev_version != CACHE_VERSION:
        logger.info(
            f"CACHE_VERSION bumped {prev_version} → {CACHE_VERSION}. "
            f"Old verdicts will age out via TTL."
        )

    FINGERPRINT_FILE.write_text(record)
