# PhishGuard

A browser trust layer that protects users from phishing today and merchant fraud
in later phases. Real-time URL/page scanning via FastAPI backend, RAG-grounded
threat intelligence, and a Chrome extension UI.

## Status

Phase 1 — URL analysis pipeline (deterministic checks, no LLM yet).

## Architecture

- **backend/** — FastAPI app, scan orchestration, signal modules
- **extension/** — Chrome WebExtension (Phase 2)
- **docs/** — Design notes and per-phase guides

## Quick start

```bash
cp .env.example .env
# Edit .env to add your VIRUSTOTAL_API_KEY (free tier: virustotal.com/gui/join-us)
docker compose up --build
```

The API will be at http://localhost:8000 with interactive docs at /docs.

Run tests:

```bash
cd backend && pip install -r requirements.txt && pytest
```

## Roadmap

| Phase | What | Status |
|-------|------|--------|
| 1 | URL analysis: typosquatting, domain age, VirusTotal, heuristics | In progress |
| 2 | Chrome extension wired to backend | Planned |
| 3 | LLM content analysis + RAG threat intel | Planned |
| 4 | Buy-scanner activation (merchant verification) | Planned |
| 5 | Auth, dashboard, scan history | Planned |
| 6 | Card-safety recommendations (Privacy.com, Apple Pay nudges) | Planned |
