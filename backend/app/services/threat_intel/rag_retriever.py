"""RAG threat-intel signal.

Embeds the URL + page title + form-field context, retrieves the k most
semantically similar known phishing patterns from a ChromaDB collection,
and produces a SignalResult based on retrieval similarity.

Why this matters even though it overlaps with the LLM signal:
- The LLM has no direct knowledge of recent phishing patterns; RAG provides
  grounded examples it (or the user) can reference
- Retrieval-only is fast (~5ms after warmup) — useful as a cheap filter
  even if the LLM signal is disabled
- The pattern matches give human-readable explanations the user can verify

Implementation notes:
- ChromaDB embedded mode (no separate server)
- sentence-transformers (all-MiniLM-L6-v2) — small, fast, runs on CPU
- Collection is loaded once at startup and cached as a module-level singleton
"""
import json
import logging
from pathlib import Path
from typing import Optional

from app.api.schemas.scan import SignalResult
from app.config import settings

logger = logging.getLogger("phishguard")

# Lazy-loaded singletons. ChromaDB and sentence-transformers are heavy imports
# (~3s cold start), so we initialize on first use rather than at module load.
_collection = None
_load_error: Optional[str] = None


def _initialize() -> None:
    """Build the ChromaDB collection from the JSONL corpus on first call.

    Idempotent — once initialized, repeated calls return immediately. If
    initialization fails, sets _load_error and the signal will fail-soft
    on every subsequent call.
    """
    global _collection, _load_error

    if _collection is not None or _load_error is not None:
        return

    try:
        # Heavy imports inside the function so module load stays fast
        import chromadb
        from chromadb.utils import embedding_functions

        corpus_path = Path(settings.rag_corpus_path)
        if not corpus_path.is_absolute():
            # Resolve relative to the backend directory (where the app runs from
            # in Docker as /app, and locally as backend/)
            backend_root = Path(__file__).resolve().parents[3]
            corpus_path = backend_root / settings.rag_corpus_path

        if not corpus_path.exists():
            _load_error = f"Corpus file not found: {corpus_path}"
            logger.warning(f"[RAG] {_load_error}")
            return

        # Use sentence-transformers for embeddings — small, CPU-friendly,
        # runs in ~50ms per query after warmup
        embedder = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.rag_embedding_model
        )

        client = chromadb.PersistentClient(path=settings.rag_chroma_path)

        # get_or_create handles the "first run" and "container restart" cases
        # the same way — collection persists across restarts via Chroma's
        # disk persistence.
        collection = client.get_or_create_collection(
            name=settings.rag_collection_name,
            embedding_function=embedder,
        )

        # If the collection is empty (first run) OR the corpus has changed
        # (more entries than indexed), rebuild it. Cheap to check, expensive
        # to skip when stale.
        with corpus_path.open() as f:
            entries = [json.loads(line) for line in f if line.strip()]

        if collection.count() < len(entries):
            logger.info(f"[RAG] Indexing {len(entries)} corpus entries…")
            # Wipe and rebuild — for a small corpus this is faster than
            # diffing entry-by-entry. Once the corpus grows past ~10k items,
            # switch to incremental indexing.
            try:
                client.delete_collection(settings.rag_collection_name)
            except Exception:
                pass
            collection = client.get_or_create_collection(
                name=settings.rag_collection_name,
                embedding_function=embedder,
            )
            collection.add(
                ids=[e["id"] for e in entries],
                documents=[e["text"] for e in entries],
                metadatas=[
                    {"category": e.get("category", ""), "source": e.get("source", "")}
                    for e in entries
                ],
            )
            logger.info(f"[RAG] Indexed {len(entries)} patterns into collection.")

        _collection = collection
    except Exception as e:
        # Sentence-transformers / HuggingFace errors are noisy. Show a clean
        # message in the user-facing explanation and put the gory details in logs.
        err_type = type(e).__name__
        if "Connection" in err_type or "OSError" in err_type or "HTTPError" in err_type:
            _load_error = "Embedding model not cached. Run with internet access at least once."
        else:
            _load_error = f"{err_type} during initialization (see backend logs)"
        logger.exception("[RAG] Initialization failed")


def _build_query(url: str, page_title: Optional[str], form_fields: list[str]) -> str:
    """Compose the text we'll embed for similarity search."""
    parts = [f"URL: {url}"]
    if page_title:
        parts.append(f"Title: {page_title}")
    if form_fields:
        parts.append(f"Form fields: {', '.join(form_fields)}")
    return " | ".join(parts)


def _score_from_similarity(distance: float) -> int:
    """Map ChromaDB cosine distance to a score contribution.

    Chroma returns distances where smaller = more similar. For all-MiniLM-L6-v2
    cosine distances, ~0.5 is meaningfully similar, <0.4 is strongly similar.
    """
    if distance < 0.4:
        return 25  # strong match — looks a lot like a known phishing pattern
    if distance < 0.6:
        return 12  # moderate match
    return 0       # weak — don't trigger


async def check_rag_threat_intel(
    url: str,
    page_title: Optional[str] = None,
    form_fields: Optional[list[str]] = None,
) -> SignalResult:
    if not settings.rag_enabled:
        return SignalResult(
            name="rag_threat_intel",
            triggered=False,
            explanation="RAG signal disabled in config.",
        )

    _initialize()

    if _load_error:
        return SignalResult(
            name="rag_threat_intel",
            triggered=False,
            explanation=f"RAG unavailable: {_load_error}",
        )

    try:
        query_text = _build_query(url, page_title, form_fields or [])

        results = _collection.query(
            query_texts=[query_text],
            n_results=settings.rag_top_k,
        )

        # Chroma returns parallel lists indexed [0] for the single query
        documents = results.get("documents", [[]])[0]
        distances = results.get("distances", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        if not distances:
            return SignalResult(
                name="rag_threat_intel",
                triggered=False,
                explanation="No similar patterns found in threat-intel corpus.",
            )

        best_distance = distances[0]
        best_doc = documents[0]
        best_category = metadatas[0].get("category", "unknown") if metadatas else "unknown"

        score = _score_from_similarity(best_distance)

        if score == 0:
            return SignalResult(
                name="rag_threat_intel",
                triggered=False,
                explanation=(
                    f"Closest pattern (distance {best_distance:.2f}, category "
                    f"'{best_category}') is too dissimilar to flag."
                ),
            )

        return SignalResult(
            name="rag_threat_intel",
            triggered=True,
            score_contribution=score,
            explanation=(
                f"Similar to known phishing pattern '{best_category}' "
                f"(similarity {1 - best_distance:.0%}): {best_doc[:160]}…"
            ),
            metadata={
                "category": best_category,
                "distance": best_distance,
                "matched_count": len(documents),
            },
        )
    except Exception as e:
        logger.exception("[RAG] Query failed")
        return SignalResult(
            name="rag_threat_intel",
            triggered=False,
            explanation=f"RAG query error: {type(e).__name__}",
        )
