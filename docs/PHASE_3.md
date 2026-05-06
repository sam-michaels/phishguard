# Phase 3 — LLM Classifier + RAG Threat Intel

## Goal

Add two new signals to the orchestrator that go beyond URL pattern matching:
an LLM-based phishing classifier (provider-agnostic — Ollama locally, Groq in
production) and a RAG-based retrieval signal grounded in a curated
phishing-pattern corpus.

## What changed

| File | Status |
|------|--------|
| `backend/requirements.txt` | +groq, +chromadb, +sentence-transformers |
| `backend/app/config.py` | CACHE_VERSION → v5, llm_provider + Ollama + Groq + RAG settings |
| `backend/app/services/content_analysis/llm_providers/` | New subpackage — provider abstraction |
| `backend/app/services/content_analysis/llm_classifier.py` | Refactored to delegate to provider |
| `backend/app/services/threat_intel/rag_retriever.py` | New |
| `backend/app/data/phishing_corpus.jsonl` | 20 curated phishing patterns |
| `backend/app/services/url_analysis/orchestrator.py` | Wires both new signals |
| `backend/app/api/routes/health.py` | Provider-agnostic LLM liveness probe |
| `backend/app/main.py` | Warms RAG collection at startup |
| `backend/tests/test_llm_classifier.py` | Updated mocks + factory tests |
| `backend/tests/test_phishing_examples.py` | Live integration tests (skipped by default) |
| `docker-compose.yml` | Passes LLM_PROVIDER, GROQ_API_KEY, GROQ_MODEL through |

## Provider abstraction

The LLM signal is provider-agnostic. `settings.llm_provider` (env:
`LLM_PROVIDER`) selects between `"ollama"` and `"groq"` at runtime:

```
llm_providers/
├── base.py      # LLMProvider ABC, ProviderConnectionError, ProviderResponseError
├── shared.py    # SYSTEM_PROMPT, _build_user_prompt, _parse_response (used by all providers)
├── ollama.py    # OllamaProvider — httpx → local Ollama HTTP API
├── groq.py      # GroqProvider — groq SDK → Groq cloud
└── factory.py   # get_provider(name) — instantiates the right class
```

**Switching providers:** set `LLM_PROVIDER=groq` (and `GROQ_API_KEY`) in your
environment or `.env` file. No code changes.

Both providers implement the same interface:
- `classify(url, page_title, form_fields) -> dict` with verdict/confidence/reasoning
- `is_reachable() -> bool` for the `/health` endpoint

## Setup — Ollama (local dev)

### 1. Install Ollama on your host machine

```bash
brew install ollama
ollama serve         # runs in background, listens on localhost:11434
```

### 2. Pull the model

```bash
ollama pull llama3.1:8b
```

This is ~4.7 GB.

### 3. Verify Ollama is reachable

```bash
curl http://localhost:11434/api/tags
```

You should see a JSON response listing your installed models.

### 4. Rebuild the backend container

```bash
docker compose down
docker compose up --build
```

The build installs ChromaDB + sentence-transformers (~2 minutes first time).

### 5. Verify health

```bash
curl http://localhost:8000/health
```

Expected:
```json
{"status":"ok","redis":true,"llm":true,"rag":true}
```

If `llm: false`, Ollama isn't reachable from the container. Check that
`ollama serve` is running. On Mac/Windows Docker Desktop this works
automatically via `host.docker.internal:11434`.

If `rag: false`, the corpus didn't index. Check the backend logs.

## Setup — Groq (production / Railway)

### 1. Get an API key

Sign up at [console.groq.com](https://console.groq.com). The free tier
covers small-scale testing.

### 2. Set environment variables

```bash
# .env (local) or Railway environment settings
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.1-8b-instant   # optional, this is the default
```

### 3. Verify

```bash
curl http://localhost:8000/health
```

`llm: true` means the API key is present (Groq has no free liveness-ping
endpoint, so key presence is the proxy). The first `/scan` call will confirm
the key actually works.

## How the new signals work

### LLM classifier

Sends the URL, page title, and form fields to the configured provider with
a structured prompt asking for a JSON verdict:

```json
{
  "verdict": "safe" | "suspicious" | "phishing",
  "confidence": 0.0 to 1.0,
  "reasoning": "one short sentence"
}
```

Score contribution:
- `phishing` × confidence × 40 (max 40 points)
- `suspicious` × confidence × 20 (max 20)
- `safe` → 0 points

Fail-soft: any provider error (unreachable, bad response, rate limit) returns
`triggered=False` and the rest of the pipeline continues unaffected.

### RAG threat intel

1. Embeds the URL + title + form context using `all-MiniLM-L6-v2`
2. Retrieves the top-5 most semantically similar entries from ChromaDB
3. Scores based on cosine similarity to the closest match:
   - distance < 0.4 → 25 points (strong match)
   - distance < 0.6 → 12 points (moderate match)
   - else → 0 points

## Performance characteristics

Per-scan latency on a fresh URL (no cache hit):

| Stage | Cold | Warm |
|-------|------|------|
| Deterministic signals (typo, heuristics, domain age, VT) | ~600ms | ~600ms |
| LLM classifier — Ollama (Llama 3.1 8B) | ~1.5s | ~1.2s |
| LLM classifier — Groq (Llama 3.1 8B Instant) | ~300ms | ~300ms |
| RAG retrieval (ChromaDB embedded + MiniLM) | ~3s | ~50ms |
| **Total (asyncio.gather, parallel)** | ~3s | ~1.2s |
| **Cache hit** | <10ms | <10ms |

The RAG cold start is the embedding model loading cost — first query only.
This is why we warm RAG at startup.

## Testing

Unit tests run without any LLM provider:

```bash
cd backend
pytest
```

Live integration tests against a running backend:

```bash
PHISHGUARD_LIVE=1 pytest tests/test_phishing_examples.py -v -s
```

## Tuning the corpus

`backend/data/phishing_corpus.jsonl` is hand-curated. After editing, restart
the backend — the collection auto-rebuilds when the corpus has more entries
than what's indexed.

Good corpus sources:
1. **PhishTank** — extract *patterns* from clusters of similar URLs, not raw URLs
2. **CISA advisories** — concrete campaign descriptions
3. **Your own observations** — when the LLM flags something the deterministic
   signals missed, add the pattern

## Common issues

**`llm: false` on `/health` with Groq**
Check that `GROQ_API_KEY` is set and non-empty in the container environment.

**`llm: false` on `/health` with Ollama**
Check that `ollama serve` is running on your host. On Linux, ensure
`extra_hosts: host.docker.internal:host-gateway` is in docker-compose.yml
(already configured).

**Groq rate limit errors in logs**
The free tier has request-per-minute limits. The cache (CACHE_VERSION=v5)
means each unique URL only hits the LLM once. High-traffic testing may still
hit limits — upgrade the Groq tier or temporarily set `LLM_ENABLED=false`.

**LLM responses are inconsistent / sometimes not valid JSON**
Both providers are asked for JSON output (`format: json` for Ollama,
`response_format: json_object` for Groq). The parser in `shared.py` also
handles fenced code blocks and preambles defensively. Hard failures fall
through to `triggered=False`.

**RAG keeps reindexing on every restart**
The collection persists at `backend/data/chroma_db/`. If that path is in a
volume mount that gets wiped, it'll rebuild. The rebuild only takes a few
seconds for the 20-entry seed corpus.
