# Cache Versioning Workflow

## TL;DR

When you change scoring logic, bump `CACHE_VERSION` in `backend/app/config.py`.
That's it — no manual Redis flush, no user impact, old verdicts auto-expire.

## Why

Cache keys are versioned: `verdict:v2:<hash-of-url>`. When the running code
looks up a cached verdict, it only finds keys matching the current version.
Bumping `v2 → v3` makes every old cached verdict instantly unreachable. The
orphaned keys age out naturally via their TTL (max 24h).

## When to bump CACHE_VERSION

✅ **Bump it for any of these:**
- Changed a `score_contribution` value in any signal
- Changed `risk_threshold_caution` or `risk_threshold_danger`
- Added a new signal to the orchestrator
- Removed an existing signal
- Changed a signal's logic in a way that affects whether `triggered` fires
- Changed the verdict label assignment (`safe` / `caution` / `danger`)

❌ **Don't bump it for:**
- Refactoring code without changing behavior
- Fixing typos in `explanation` strings
- Renaming variables or functions
- Adding code comments
- Reformatting / linting changes

## How to bump

Open `backend/app/config.py`. Change:

```python
CACHE_VERSION = "v2"
```

to:

```python
CACHE_VERSION = "v3"
```

That's the entire change. Save the file. Uvicorn's `--reload` picks it up
automatically. The next scan of any URL will compute fresh and write under
the new version.

## The safety check

If you forget to bump the version after changing scoring code, you'll see this
warning at backend startup:

```
WARNING:phishguard:⚠ SCORING CODE CHANGED but CACHE_VERSION (v2) was NOT bumped.
   If this change affects scores, bump CACHE_VERSION in app/config.py
   so old cached verdicts become unreachable.
```

The check fingerprints the contents of all scoring files and compares against
what was running last time. It's just a warning, not an error — sometimes you
genuinely refactored without changing scores. But take a moment to consider
before ignoring it.

## What users experience during a version bump

**Nothing.** Pages load at normal speed. The first scan of any URL after the
bump takes the usual ~500ms-2s while signals run, then gets cached under the
new version. Subsequent scans of that URL are fast again.

There's no cold-start latency spike because:
1. Most-visited URLs get re-cached within minutes
2. The old cache entries still exist in Redis; they're just unreachable —
   if you needed to roll back to the previous version, those entries would
   immediately become readable again
3. Cache misses don't queue up; each URL is independently scanned on demand

## The pattern in production systems

This is the same approach used by:
- **CDNs** (versioned asset URLs: `app.v3.css` instead of `app.css`)
- **Browser caches** (file-content-hashed asset names from webpack/vite)
- **Database migrations** (schema version numbers gating reads)
- **Mobile apps** (API version in the URL path: `/v2/users` vs `/v3/users`)

The principle is the same in all of them: **make the cache key a function of
the data's shape, not just its identity**, so that changes to shape
automatically invalidate old entries.
