# Phase 1 — URL Analysis Pipeline

## Goal

A FastAPI backend that accepts a URL and returns a risk verdict using only
deterministic + reputation-API checks. **No LLM yet.** This is your foundation —
once you trust this layer, every later phase plugs into it.

## What you're building (and why)

The pipeline runs four signals in parallel:

| Signal | What it catches | Why include it |
|--------|-----------------|----------------|
| **Typosquatting** (Levenshtein) | `paypa1.com`, `gooogle.com` | Cheap, instant, near-zero false positives at distance=1 |
| **Domain age** (WHOIS) | Brand-new domains pretending to be banks | Phishing kits launch on fresh domains daily |
| **VirusTotal** (60+ vendor lookup) | Already-known malicious URLs | Free reputation data — no reason not to use it |
| **Heuristics** (regex / parsing) | IP-as-host, `@` tricks, `.tk`/`.ml` TLDs | Catches lazy phishers in microseconds |

Each signal returns a `SignalResult` with a contribution to the risk score.
The `aggregate_signals` function sums them, caps at 100, and assigns a
verdict label (`safe` / `caution` / `danger`).

The whole pipeline is wrapped in a Redis cache. Same URL within an hour → cached
verdict, no API calls, sub-millisecond response.

## Architectural decisions worth understanding

**Why parallel checks?** `asyncio.gather` runs all four checks concurrently.
Total latency = max of any single check, not sum. Domain WHOIS is the slowest
(~1–2s); VT is ~200–500ms; the others are <1ms. Running them sequentially would
be 2–3 seconds; in parallel it's ~1.5s on a cold scan, <50ms on a cache hit.

**Why each signal has its own module?** When you add Phase 4 (buy-scanner), the
merchant module will reuse `domain_age` and `virustotal` directly. Keeping each
check as a single-responsibility module makes that reuse trivial.

**Why a `merchant` route stub already?** Locks the API contract early. When the
extension goes in (Phase 2), it can be wired to `/api/v1/merchant/scan` from
day one — the endpoint just returns 501 until Phase 4. No future breaking
changes for clients.

**Why TTL by verdict label?** Safe results expire fast (1h) because a domain
can be compromised. Danger results stay cached longer (24h) because they're
unlikely to flip back to safe quickly — and you don't want to keep re-paying VT
quota on the same bad URL.

## Running locally

```bash
# 1. Get a free VirusTotal API key
#    https://www.virustotal.com/gui/join-us

# 2. Configure env
cp .env.example .env
# Edit .env, set VIRUSTOTAL_API_KEY=...

# 3. Bring up Redis + backend
docker compose up --build

# 4. Hit the API
curl -X POST http://localhost:8000/api/v1/scan/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://paypa1.com/login"}'

# Or open http://localhost:8000/docs for interactive Swagger UI
```

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest
```

You should see ~15 passing tests. The endpoint test for a legitimate URL runs
real WHOIS / VT calls — if your environment can't reach those, that test may be
slow or skip the relevant signal.

## "Phase 1 is complete when..."

- [ ] `docker compose up` brings backend + Redis up cleanly
- [ ] `POST /api/v1/scan/url` with `https://www.google.com/` returns verdict `safe`
- [ ] `POST /api/v1/scan/url` with `https://paypa1.com/login` returns verdict `caution` or `danger`
- [ ] Repeated POST of the same URL returns `cached: true` on the second call
- [ ] All tests pass (`pytest`)
- [ ] You can read each module without referencing this doc

## What you should poke at before Phase 2

1. **Threshold tuning.** Try 50 random real URLs from your browser history. Are
   any flagged incorrectly? Bump `risk_threshold_caution` / `risk_threshold_danger`
   in `config.py` until verdicts match your intuition.
2. **Add to `POPULAR_DOMAINS`.** Your typosquatting detector is only as good as
   the targets it knows. Add 20 more. Aim for sites your eventual users actually
   use — Canadian retail, your university SSO, etc.
3. **Extra heuristics.** Read PhishTank's recent submissions for an hour. Notice
   patterns? Add them as new heuristic checks.

## Phase 2 preview

Browser extension. The backend already accepts `page_title` and `form_fields`
in `URLScanRequest` — those become content-script payloads. The extension's
`background.js` calls `/api/v1/scan/url` on every navigation and renders a
red/yellow/green badge based on `verdict`.
